"""
FastAPI backend wrapping the CSP solver and min-conflicts repair.

Rule 4: the solver itself (phase1_csp) and repair (min_conflicts.py) stay
pure -- no FastAPI/HTTP code inside them. This file's only job is
translating HTTP requests into calls against those pure modules and
serializing the results back to JSON. All allocation/repair DECISIONS
still happen in the CSP solver and min-conflicts -- this layer contains
zero decision logic of its own.
"""

from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "phase1_csp"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from problem import build_problem, CSPProblem
from constraints import apply_capacity_constraint
from ac3 import ac3
from solver import solve as csp_solve

from min_conflicts import repair as run_repair, total_conflicts
from disruptions import tanker_breakdown, urgent_request

app = FastAPI(title="Water Tanker Dispatch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state for the demo: the current problem + its current schedule.
# A real deployment would persist this; this is a validated simulation
# (CLAUDE.md), so process memory is enough.
_state = {"problem": None, "assignment": None}


def _fresh_problem() -> CSPProblem:
    problem = build_problem()
    apply_capacity_constraint(problem)
    ac3(problem)
    return problem


def _serialize_assignment(problem: CSPProblem, assignment: dict) -> dict:
    schedule = []
    for t in problem.tankers:
        row = {"tanker_id": t.id, "capacity_liters": t.capacity_liters, "slots": []}
        for slot in range(problem.num_slots):
            row["slots"].append(assignment.get((t.id, slot)))
        schedule.append(row)
    return {
        "schedule": schedule,
        "num_slots": problem.num_slots,
        "zones": [
            {"name": z.name, "need_liters": z.need_liters, "is_high_priority": z.is_high_priority}
            for z in problem.zones
        ],
    }


@app.post("/api/generate")
def generate_schedule():
    """Build a fresh problem and solve it from scratch (Phase 1's solver)."""
    problem = _fresh_problem()
    solution, stats = csp_solve(problem, "mrv+degree", "lcv")
    if solution is None:
        raise HTTPException(status_code=500, detail="CSP unsatisfiable with current fleet/zones")

    _state["problem"] = problem
    _state["assignment"] = solution

    return {
        **_serialize_assignment(problem, solution),
        "nodes_explored": stats.nodes_explored,
    }


class BreakdownRequest(BaseModel):
    tanker_id: str


@app.post("/api/disrupt/breakdown")
def disrupt_breakdown(req: BreakdownRequest):
    """Mark a tanker unavailable, then repair the schedule via min-conflicts."""
    problem, assignment = _state["problem"], _state["assignment"]
    if problem is None or assignment is None:
        raise HTTPException(status_code=400, detail="Generate a schedule first")

    valid_ids = {t.id for t in problem.tankers}
    if req.tanker_id not in valid_ids:
        raise HTTPException(status_code=404, detail=f"Unknown tanker '{req.tanker_id}'")

    broken = tanker_breakdown(problem, assignment, req.tanker_id)
    repaired, diff, steps = run_repair(problem, broken, seed=1)

    if repaired is None:
        raise HTTPException(status_code=500, detail="Repair failed to converge")

    _state["assignment"] = repaired

    return {
        **_serialize_assignment(problem, repaired),
        "diff": [
            {"tanker_id": v["variable"][0], "slot": v["variable"][1], "from": v["from"], "to": v["to"]}
            for v in diff
        ],
        "repair_steps": steps,
    }


class UrgentRequest(BaseModel):
    zone_name: str


@app.post("/api/disrupt/urgent")
def disrupt_urgent(req: UrgentRequest):
    """Escalate an already-entitled, currently-unscheduled zone; repair to insert it."""
    problem, assignment = _state["problem"], _state["assignment"]
    if problem is None or assignment is None:
        raise HTTPException(status_code=400, detail="Generate a schedule first")

    valid_zones = {z.name for z in problem.zones}
    if req.zone_name not in valid_zones:
        raise HTTPException(status_code=404, detail=f"Unknown zone '{req.zone_name}' (not entitled)")

    broken = urgent_request(problem, assignment, req.zone_name)
    must_serve = frozenset({req.zone_name})
    repaired, diff, steps = run_repair(problem, broken, seed=1, must_serve=must_serve)

    if repaired is None:
        raise HTTPException(status_code=500, detail="Repair failed to converge")

    _state["assignment"] = repaired

    return {
        **_serialize_assignment(problem, repaired),
        "diff": [
            {"tanker_id": v["variable"][0], "slot": v["variable"][1], "from": v["from"], "to": v["to"]}
            for v in diff
        ],
        "repair_steps": steps,
    }
