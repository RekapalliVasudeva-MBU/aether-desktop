"""Antigravity Planner Engine: Multi-phase autonomous plan generation and step tracking.

Phases:
1. Research  - Discover files, perform web/local searches, slice-read code.
2. Plan      - Outline structured subtasks and invariants.
3. Execute   - Apply surgical edits, create artifacts, build deliverables.
4. Verify    - Run verification, test deliverables, ensure zero regression.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional


class PlanStep:
    def __init__(self, id: str, title: str, status: str = "pending"):
        self.id = id
        self.title = title
        self.status = status  # pending, in_progress, completed, failed

    def to_dict(self) -> Dict:
        return {"id": self.id, "title": self.title, "status": self.status}


class ExecutionPlan:
    def __init__(self, phase: str = "research", steps: Optional[List[PlanStep]] = None):
        self.phase = phase
        self.steps = steps or []

    def set_phase(self, phase: str) -> None:
        self.phase = phase

    def add_step(self, id: str, title: str) -> None:
        self.steps.append(PlanStep(id, title))

    def update_step(self, id: str, status: str) -> None:
        for s in self.steps:
            if s.id == id:
                s.status = status

    def to_dict(self) -> Dict:
        return {
            "phase": self.phase,
            "steps": [s.to_dict() for s in self.steps]
        }


def create_initial_plan(task_description: str) -> ExecutionPlan:
    """Create a structured execution plan for complex requests."""
    plan = ExecutionPlan(phase="research")
    plan.add_step("research", "Gather information & inspect requirements")
    plan.add_step("plan", "Formulate implementation approach & structure")
    plan.add_step("execute", "Execute tool actions & generate deliverables")
    plan.add_step("verify", "Verify output files and confirm delivery")
    return plan
