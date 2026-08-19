"""Apache Burr State Machine Orchestrator for Aether Desktop.

State -> Action -> State Architecture:
  - Central Burr Application state tracking goals, steps, pending approvals, checkpoints.
  - Human-in-the-Loop (HITL) approval pause/resume for sensitive actions.
  - Snapshot checkpointing & rollback capability.
  - Dynamic per-action model selection.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Generator, Optional, Tuple

from burr.core import action, State, ApplicationBuilder, default

from . import config, provider, agent, rag, tools, memory, skills

CHECKPOINTS_DIR = config.AETHER_HOME / "checkpoints"
CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)

# Active running Burr applications map: session_id -> { "app": Application, "state": dict }
ACTIVE_BURR_APPS: Dict[str, Any] = {}
PENDING_APPROVALS: Dict[str, Dict[str, Any]] = {}


# ---- BURR ACTIONS ----

@action(
    reads=["user_goal", "mode", "rag_context"],
    writes=["plan", "current_step_index", "status", "accumulated_context"]
)
def plan_action(state: State) -> Tuple[dict, State]:
    """Burr Action: Analyze goal and generate task plan."""
    user_goal = state["user_goal"]
    mode = state.get("mode", "normal")
    rag_context = state.get("rag_context", "")

    plan_prompt = (
        f"Analyze the following user goal and break it down into 2-4 subtasks for specialized subagents.\n"
        f"Available Subagents:\n"
        f"- 'rag': PDF & document retrieval\n"
        f"- 'research': Web search & external knowledge\n"
        f"- 'code': Command execution, local file manipulation, python runs\n"
        f"- 'synthesis': Aggregating findings into final response\n\n"
        f"User Goal: {user_goal}\n\n"
        f"Respond ONLY with a valid JSON array of subtasks, e.g.:\n"
        f'[\n  {{"subagent": "research", "subtask": "Search for latest python fast API features"}},\n'
        f'  {{"subagent": "synthesis", "subtask": "Synthesize research into a summary"}}\n]'
    )

    tasks = []
    try:
        model = config.get_role_model("planner")
        resp = provider.chat([{"role": "user", "content": plan_prompt}], model=model, stream=False)
        raw = resp.choices[0].message.content or "[]"
        if "```json" in raw:
            raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in raw:
            raw = raw.split("```", 1)[1].split("```", 1)[0].strip()
        tasks = json.loads(raw)
    except Exception:
        pass

    if not isinstance(tasks, list) or len(tasks) == 0:
        if mode == "rag":
            tasks = [
                {"subagent": "rag", "subtask": f"Retrieve document context for: {user_goal}"},
                {"subagent": "synthesis", "subtask": "Synthesize context into response"}
            ]
        else:
            tasks = [
                {"subagent": "research", "subtask": f"Investigate: {user_goal}"},
                {"subagent": "synthesis", "subtask": "Synthesize findings into final response"}
            ]

    init_context = ""
    if rag_context:
        init_context += f"Initial RAG Context:\n{rag_context}\n\n"

    result = {
        "plan": tasks,
        "current_step_index": 0,
        "status": "planned",
        "accumulated_context": init_context
    }
    return result, state.update(**result)


@action(
    reads=["plan", "current_step_index", "accumulated_context", "session_id"],
    writes=["current_step_index", "accumulated_context", "last_tool_call", "status", "pending_approval"]
)
def execute_step_action(state: State) -> Tuple[dict, State]:
    """Burr Action: Execute active subtask in state machine."""
    plan = state.get("plan", [])
    idx = state.get("current_step_index", 0)
    sid = state.get("session_id", "default")
    accumulated_context = state.get("accumulated_context", "")

    if idx >= len(plan):
        res = {"status": "plan_completed"}
        return res, state.update(**res)

    task = plan[idx]
    agent_key = task.get("subagent", "research")
    subtask_desc = task.get("subtask", "")

    role_model = config.get_role_model(agent_key)

    # Subagent execution logic
    subagent_system = f"You are the {agent_key.upper()} specialist worker for Aether Desktop.\nContext:\n{accumulated_context}"
    messages = [
        {"role": "system", "content": subagent_system},
        {"role": "user", "content": subtask_desc}
    ]

    all_schemas = agent.get_external_tool_schemas()
    resp = provider.chat(messages, model=role_model, stream=False, tools=all_schemas)
    msg = resp.choices[0].message
    content = msg.content or ""
    tool_calls = getattr(msg, "tool_calls", None)

    pending_hitl = None
    exec_result_text = content

    if tool_calls:
        for tc in tool_calls:
            fn = tc.function
            try:
                args = json.loads(fn.arguments or "{}")
            except Exception:
                args = {}

            # Human-in-the-Loop check for sensitive tool calls
            sensitive_tools = ["terminal", "run_python", "write_file", "write_to_file", "mcp_add_server", "mcp_remove_server"]
            if fn.name in sensitive_tools and config.is_hitl_enabled():
                pending_hitl = {
                    "tool": fn.name,
                    "args": args,
                    "subagent": agent_key,
                    "reason": f"Tool '{fn.name}' requires Human-in-the-Loop approval before execution."
                }
                PENDING_APPROVALS[sid] = pending_hitl
                res = {
                    "status": "awaiting_approval",
                    "pending_approval": pending_hitl,
                    "current_step_index": idx
                }
                return res, state.update(**res)

            res_tool = tools.call_tool(fn.name, args)
            exec_result_text += f"\n[Tool {fn.name} executed]: {res_tool}\n"

    new_context = accumulated_context + f"\n--- Step {idx+1} ({agent_key}): {subtask_desc} ---\n{exec_result_text}\n"

    result = {
        "current_step_index": idx + 1,
        "accumulated_context": new_context,
        "last_tool_call": None,
        "pending_approval": None,
        "status": "executing"
    }
    return result, state.update(**result)


@action(
    reads=["accumulated_context", "user_goal"],
    writes=["final_response", "status"]
)
def synthesize_action(state: State) -> Tuple[dict, State]:
    """Burr Action: Final response synthesis."""
    user_goal = state["user_goal"]
    accumulated_context = state.get("accumulated_context", "")

    synth_prompt = f"Provide the final comprehensive response to the user goal: '{user_goal}' using the gathered context below:\n\n{accumulated_context}"
    model = config.get_role_model("synthesis")

    resp = provider.chat([{"role": "user", "content": synth_prompt}], model=model, stream=False)
    final_text = resp.choices[0].message.content or "Completed task."

    result = {
        "final_response": final_text,
        "status": "completed"
    }
    return result, state.update(**result)


# ---- CHECKPOINTING HELPERS ----

def save_checkpoint(session_id: str, state_data: dict) -> str:
    """Save a state snapshot checkpoint to disk."""
    sdir = CHECKPOINTS_DIR / session_id
    sdir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    cid = f"cp_{ts}"
    fp = sdir / f"{cid}.json"
    fp.write_text(json.dumps(state_data, indent=2, ensure_ascii=False), encoding="utf-8")
    return cid


def list_checkpoints(session_id: str) -> List[Dict[str, Any]]:
    """List saved checkpoints for a session."""
    sdir = CHECKPOINTS_DIR / session_id
    if not sdir.exists():
        return []
    cps = []
    for fp in sorted(sdir.glob("*.json"), reverse=True):
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
            cps.append({
                "id": fp.stem,
                "timestamp": fp.stat().st_mtime,
                "status": d.get("status"),
                "step_index": d.get("current_step_index", 0)
            })
        except Exception:
            continue
    return cps


def rollback_checkpoint(session_id: str, checkpoint_id: str) -> Optional[dict]:
    """Rollback session state to a specific checkpoint."""
    fp = CHECKPOINTS_DIR / session_id / f"{checkpoint_id}.json"
    if not fp.exists():
        return None
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        if session_id in ACTIVE_BURR_APPS:
            ACTIVE_BURR_APPS[session_id]["state"] = data
        return data
    except Exception:
        return None


# ---- BURR APPLICATION MANAGER ----

from burr.core import action, State, ApplicationBuilder, default, expr

class BurrOrchestrator:
    """Manager for Burr State Machine Application runs."""

    def __init__(self, session_id: str, user_goal: str, mode: str = "normal", rag_context: str = ""):
        self.session_id = session_id
        self.user_goal = user_goal
        self.mode = mode
        self.rag_context = rag_context

        # Build Burr Application Graph
        self.app = (
            ApplicationBuilder()
            .with_actions(
                plan=plan_action,
                execute_step=execute_step_action,
                synthesize=synthesize_action
            )
            .with_entrypoint("plan")
            .with_transitions(
                ("plan", "execute_step", default),
                ("execute_step", "execute_step", expr("status == 'executing'")),
                ("execute_step", "synthesize", default)
            )
            .with_state(
                session_id=session_id,
                user_goal=user_goal,
                mode=mode,
                rag_context=rag_context,
                plan=[],
                current_step_index=0,
                accumulated_context="",
                status="initialized",
                pending_approval=None,
                final_response=""
            )
            .build()
        )
        ACTIVE_BURR_APPS[session_id] = {"app": self.app, "state": dict(self.app.state)}

    def stream_execution(self) -> Generator[Dict[str, Any], None, None]:
        """Stream Burr state machine execution events."""
        yield {"type": "status", "data": "Burr State Machine initializing..."}

        # Step 1: Run Planning Action
        action_obj, result, new_state = self.app.step()
        save_checkpoint(self.session_id, dict(new_state))

        # Step 2: Loop Execute Action Node
        while True:
            st = self.app.state
            status = st.get("status")
            if status == "awaiting_approval":
                yield {
                    "type": "awaiting_approval",
                    "data": st.get("pending_approval")
                }
                break

            if status in ("plan_completed", "completed") or st.get("current_step_index", 0) >= len(st.get("plan", [])):
                break

            idx = st.get("current_step_index", 0)
            plan = st.get("plan", [])
            task = plan[idx] if idx < len(plan) else {}

            yield {
                "type": "subagent_start",
                "data": {
                    "index": idx + 1,
                    "total": len(plan),
                    "subagent": task.get("subagent", "worker"),
                    "role": f"{task.get('subagent', 'worker').upper()} Specialist",
                    "subtask": task.get("subtask", "")
                }
            }

            action_obj, result, new_state = self.app.step()
            save_checkpoint(self.session_id, dict(new_state))

            if new_state.get("status") == "awaiting_approval":
                yield {
                    "type": "awaiting_approval",
                    "data": new_state.get("pending_approval")
                }
                break

            yield {
                "type": "subagent_done",
                "data": {
                    "subagent": task.get("subagent", "worker"),
                    "summary": "Step completed in Burr State Machine."
                }
            }

        # Step 3: Run Synthesize if ready
        if self.app.state.get("status") in ("plan_completed", "executing") and not self.app.state.get("pending_approval"):
            action_obj, result, new_state = self.app.step()
            save_checkpoint(self.session_id, dict(new_state))
            yield {
                "type": "final_answer",
                "data": new_state.get("final_response", "Task completed.")
            }
