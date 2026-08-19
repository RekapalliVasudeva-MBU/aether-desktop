"""Multi-Agent Orchestrator for Aether Desktop.

Provides hierarchical agent coordination:
  - CoordinatorAgent: analyzes the top-level task and manages subagents.
  - Specialized Subagents:
      * RAGSubagent (PDF grounded knowledge retrieval)
      * ResearchSubagent (web search + web scraping)
      * ToolExecutionSubagent (code execution, file operations, system tools)
      * SynthesisSubagent (merging outputs into a comprehensive final response)
  - Real-time event streaming for UI task timelines (Hermes Desktop style).
"""
from __future__ import annotations

import json
import time
from typing import Dict, List, Any, Generator, Optional

from . import config, provider, agent, rag, tools, memory, skills


class Subagent:
    """Represents an isolated subagent worker focused on a specific subtask."""

    def __init__(self, name: str, role: str, system_prompt: str, tools_allowed: List[str] = None):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.tools_allowed = tools_allowed or []

    def execute(self, subtask_prompt: str, context: str = "") -> Dict[str, Any]:
        """Execute a subtask synchronously and return structured output."""
        full_system = f"{self.system_prompt}\n\nYour Role: {self.role}\nContext provided by Coordinator:\n{context}"
        messages = [
            {"role": "system", "content": full_system},
            {"role": "user", "content": subtask_prompt},
        ]
        
        all_schemas = agent.get_external_tool_schemas()
        if self.tools_allowed:
            schemas = [
                s for s in all_schemas
                if (s["function"]["name"] if "function" in s else s.get("name")) in self.tools_allowed
            ]
        else:
            schemas = all_schemas

        resp = provider.chat(messages, stream=False, tools=schemas if schemas else None)
        msg = resp.choices[0].message
        content = msg.content or ""
        tool_calls = getattr(msg, "tool_calls", None)

        tool_outputs = []
        if tool_calls:
            for tc in tool_calls:
                fn = tc.function
                try:
                    args = json.loads(fn.arguments or "{}")
                except Exception:
                    args = {}
                res = tools.call_tool(fn.name, args)
                tool_outputs.append({"tool": fn.name, "args": args, "result": res})

        return {
            "subagent": self.name,
            "role": self.role,
            "result": content,
            "tool_calls": tool_outputs,
        }


class Orchestrator:
    """Main Multi-Agent Coordinator engine."""

    def __init__(self):
        self.subagents = {
            "rag": Subagent(
                name="RAGSpecialist",
                role="PDF Knowledge & Document Retrieval",
                system_prompt="You are a RAG research specialist. Extract and explain facts strictly from retrieved PDF documents.",
                tools_allowed=["grep_search", "view_file", "read_file", "list_files"]
            ),
            "research": Subagent(
                name="WebResearcher",
                role="Web Search & External Knowledge",
                system_prompt="You are an external research specialist. Perform targeted web searches to gather accurate up-to-date information.",
                tools_allowed=["web_search", "fetch_url"]
            ),
            "code": Subagent(
                name="ToolRunner",
                role="Code & System Operations Specialist",
                system_prompt="You are a system execution specialist. Perform local file operations, command execution, and python code runs.",
                tools_allowed=["terminal", "run_python", "grep_search", "view_file", "replace_file_content", "write_to_file", "read_file", "write_file", "list_files"]
            ),
            "synthesis": Subagent(
                name="Synthesizer",
                role="Final Aggregator & Editor",
                system_prompt="You are the lead synthesizing editor. Take subagent findings, combine them logically, resolve contradictions, and format the final polished response (using Markdown, tables, and TeX math formulas when appropriate).",
                tools_allowed=[]
            )
        }

    def plan_task(self, prompt: str, mode: str = "normal") -> List[Dict[str, str]]:
        """Coordinator breaks down the prompt into subtask steps."""
        plan_prompt = (
            f"Analyze the following user goal and break it down into 2-4 subtasks for specialized subagents.\n"
            f"Available Subagents:\n"
            f"- 'rag': PDF & document retrieval\n"
            f"- 'research': Web search & web content extraction\n"
            f"- 'code': Command execution, local file manipulation, python runs\n"
            f"- 'synthesis': Aggregating findings into final polished response\n\n"
            f"User Goal: {prompt}\n\n"
            f"Respond ONLY with a valid JSON array of subtasks, e.g.:\n"
            f'[\n  {{"subagent": "research", "subtask": "Search for latest python fast API features"}},\n'
            f'  {{"subagent": "synthesis", "subtask": "Synthesize research into a summary"}}\n]'
        )

        try:
            resp = provider.chat([{"role": "user", "content": plan_prompt}], stream=False)
            raw = resp.choices[0].message.content or "[]"
            if "```json" in raw:
                raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in raw:
                raw = raw.split("```", 1)[1].split("```", 1)[0].strip()
            tasks = json.loads(raw)
            if isinstance(tasks, list) and len(tasks) > 0:
                return tasks
        except Exception:
            pass

        if mode == "rag":
            return [
                {"subagent": "rag", "subtask": f"Retrieve document context for: {prompt}"},
                {"subagent": "synthesis", "subtask": "Synthesize context into response"}
            ]
        return [
            {"subagent": "research", "subtask": f"Investigate: {prompt}"},
            {"subagent": "synthesis", "subtask": "Synthesize findings into final response"}
        ]

    def stream_orchestration(
        self, prompt: str, mode: str = "normal", rag_context: str = ""
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream execution events for multi-agent progress (SSE format compatible)."""
        yield {"type": "status", "data": "Orchestrator analyzing task..."}

        tasks = self.plan_task(prompt, mode=mode)
        yield {
            "type": "plan",
            "data": {
                "count": len(tasks),
                "tasks": tasks
            }
        }

        accumulated_context = ""
        if rag_context:
            accumulated_context += f"Initial RAG Context:\n{rag_context}\n\n"

        for idx, task in enumerate(tasks):
            agent_key = task.get("subagent", "research")
            subtask_desc = task.get("subtask", prompt)
            worker = self.subagents.get(agent_key, self.subagents["research"])

            yield {
                "type": "subagent_start",
                "data": {
                    "index": idx + 1,
                    "total": len(tasks),
                    "subagent": worker.name,
                    "role": worker.role,
                    "subtask": subtask_desc
                }
            }

            time.sleep(0.1)

            if agent_key == "rag" and not rag_context:
                try:
                    ret_text, cits = rag.retrieve_with_citations(subtask_desc)
                    accumulated_context += f"RAG Search Output:\n{ret_text}\n"
                    yield {
                        "type": "subagent_thought",
                        "data": {"subagent": worker.name, "thought": f"Retrieved {len(cits)} document citations."}
                    }
                except Exception as e:
                    yield {
                        "type": "subagent_thought",
                        "data": {"subagent": worker.name, "thought": f"RAG retrieval notice: {e}"}
                    }

            output = worker.execute(subtask_prompt=subtask_desc, context=accumulated_context)
            res_text = output.get("result", "")
            tool_calls = output.get("tool_calls", [])

            for tc in tool_calls:
                yield {
                    "type": "subagent_tool",
                    "data": {
                        "subagent": worker.name,
                        "tool": tc["tool"],
                        "args": tc["args"]
                    }
                }

            if res_text:
                accumulated_context += f"\n--- Output from {worker.name} ({worker.role}) ---\n{res_text}\n"

            yield {
                "type": "subagent_done",
                "data": {
                    "subagent": worker.name,
                    "summary": res_text[:120] if res_text else "Task step complete."
                }
            }

        if "Synthesizer" not in accumulated_context:
            final_worker = self.subagents["synthesis"]
            yield {
                "type": "subagent_start",
                "data": {
                    "index": len(tasks) + 1,
                    "total": len(tasks) + 1,
                    "subagent": final_worker.name,
                    "role": final_worker.role,
                    "subtask": "Final Response Synthesis"
                }
            }
            final_out = final_worker.execute(
                subtask_prompt=f"Provide the final answer for the user prompt: {prompt}",
                context=accumulated_context
            )
            final_text = final_out.get("result", "")
        else:
            final_text = accumulated_context

        yield {
            "type": "final_answer",
            "data": final_text
        }


def orchestrate_task(prompt: str, mode: str = "normal", rag_context: str = "") -> str:
    """Synchronous entry point for multi-agent task execution."""
    orc = Orchestrator()
    final_result = ""
    for event in orc.stream_orchestration(prompt, mode=mode, rag_context=rag_context):
        if event["type"] == "final_answer":
            final_result = event["data"]
    return final_result or "Task completed."
