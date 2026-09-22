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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "phase0_entitlement"))
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

from logic import Clause, Term
from parser import parse_kb
from engine import Engine as EntitlementEngine

ENTITLEMENT_KB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "phase0_entitlement", "knowledge_base.txt"
)
ENTITLEMENT_RULES = parse_kb(ENTITLEMENT_KB_PATH)

# Phase 2 routing + Phase 5 LLM layer are appended to sys.path AFTER
# phase0's, so phase0's `parser` module keeps priority (phase2 has no
# module of that name, but the ordering makes the intent explicit).
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "phase2_routing"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "phase5_agentic"))

from route_geometry import build_route_geometry, nearest_station_to_zone  # noqa: E402
from zones_data import ZONE_COORDS, SOURCE_STATIONS  # noqa: E402

# Route polylines are precomputed/cached by phase2 (real A* over the
# Chennai road graph) -- loading them here keeps the ~57MB graph out of
# the request path entirely.
ROUTE_GEOMETRY = build_route_geometry()

# Fixed lookup table, NOT an LLM/NL parser (Rule 2: the LLM never decides
# entitlement; it only ever produces structured facts). Phase 5 will
# replace this dropdown-driven lookup with real NL parsing that still
# outputs the same tank_level/days_since_delivery facts for this SAME
# logic engine to decide on -- the engine call below does not change.
CONDITION_TO_TANK_LEVEL = {
    "empty": 5,
    "very_low": 15,
    "low": 25,
    "ok": 60,
    "full": 95,
}

app = FastAPI(title="Water Tanker Dispatch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # dispatcher dashboard (phase3)
        "http://localhost:5175",  # volunteer view (phase4)
        "http://localhost:5176",  # driver view (phase4)
        "http://localhost:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state for the demo: the current problem + its current schedule.
# A real deployment would persist this; this is a validated simulation
# (CLAUDE.md), so process memory is enough.
_state = {
    "problem": None,
    "assignment": None,
    # (tanker_id, slot) pairs a driver has marked delivered. Purely a
    # STATUS flag: completions never alter the CSP assignment, so the
    # solver stays pure (Rule 4) and the dashboard can still show what was
    # planned alongside what actually got done.
    "completed": set(),
}


def _fresh_problem() -> CSPProblem:
    problem = build_problem()
    apply_capacity_constraint(problem)
    ac3(problem)
    return problem


def _serialize_assignment(problem: CSPProblem, assignment: dict) -> dict:
    completed = _state["completed"]
    schedule = []
    for t in problem.tankers:
        row = {
            "tanker_id": t.id,
            "capacity_liters": t.capacity_liters,
            "slots": [],
            "completed_slots": [],
        }
        for slot in range(problem.num_slots):
            row["slots"].append(assignment.get((t.id, slot)))
            if (t.id, slot) in completed:
                row["completed_slots"].append(slot)
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


ENTITLED_ZONE_NAMES = [z.name for z in build_problem().zones]


class VolunteerReport(BaseModel):
    zone_name: str
    condition: str  # one of CONDITION_TO_TANK_LEVEL's keys, from a fixed dropdown


@app.get("/api/volunteer/zones")
def volunteer_zones():
    """Zones + the fixed condition options a volunteer can pick from."""
    return {
        "zones": ENTITLED_ZONE_NAMES,
        "conditions": list(CONDITION_TO_TANK_LEVEL.keys()),
    }


@app.post("/api/volunteer/report")
def volunteer_report(req: VolunteerReport):
    """
    Submit a zone condition report; return the entitlement engine's
    decision (Phase 0), never a decision made by this layer or an LLM
    (Rule 2). `condition` must be one of the fixed dropdown values --
    translated to a tank_level fact via CONDITION_TO_TANK_LEVEL, a plain
    lookup table, not NL parsing.
    """
    if req.condition not in CONDITION_TO_TANK_LEVEL:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown condition '{req.condition}', must be one of {list(CONDITION_TO_TANK_LEVEL)}",
        )

    tank_level = CONDITION_TO_TANK_LEVEL[req.condition]
    # days_since_delivery isn't something a volunteer would know firsthand;
    # assume "just reported, so treat as 0 days since last KNOWN delivery"
    # -- entitlement then rests on the tank_level fact the volunteer gave,
    # which is the honest, available signal here.
    volunteer_facts = [
        Clause(Term("tank_level", (req.zone_name, tank_level))),
        Clause(Term("days_since_delivery", (req.zone_name, 0))),
    ]
    engine = EntitlementEngine(ENTITLEMENT_RULES + volunteer_facts)

    entitled_results = engine.backward_chain(Term("entitled", (req.zone_name,)))
    priority_results = engine.backward_chain(Term("high_priority", (req.zone_name,)))

    if not entitled_results:
        return {
            "zone_name": req.zone_name,
            "entitled": False,
            "high_priority": False,
            "reason": f"Reported tank level ({tank_level}%) and delivery history do not currently meet entitlement thresholds.",
            "estimated_slot": None,
        }

    is_high_priority = bool(priority_results)
    reason = priority_results[0][1].pretty() if priority_results else entitled_results[0][1].pretty()

    estimated_slot = None
    problem, assignment = _state["problem"], _state["assignment"]
    if problem is not None and assignment is not None:
        for t in problem.tankers:
            for slot in range(problem.num_slots):
                if assignment.get((t.id, slot)) == req.zone_name:
                    estimated_slot = {"tanker_id": t.id, "slot": slot}
                    break

    return {
        "zone_name": req.zone_name,
        "entitled": True,
        "high_priority": is_high_priority,
        "reason": reason,
        "estimated_slot": estimated_slot,
        "estimated_slot_note": (
            None
            if estimated_slot
            else "Not yet scheduled today -- pending dispatch."
        ),
    }


class ChatMessage(BaseModel):
    message: str


@app.post("/api/volunteer/chat")
def volunteer_chat(req: ChatMessage):
    """
    Plain-language volunteer message -> decision.

    RULE 2 BOUNDARY, in order:
      1. The LLM (phase5 parsing.py) ONLY extracts structured facts from
         the message and they are validated before anything else runs.
      2. Phase 0's entitlement engine ALONE decides entitled/priority,
         from those facts. The LLM is never asked, and never sees, the
         decision rules.
      3. The LLM (phase5 explain.py) then rewrites the engine's own proof
         trace into plain language -- it may not add or change any fact.
    """
    from parsing import parse_message, ParseError  # imported lazily: needs GROQ_API_KEY
    from explain import explain_decision

    try:
        facts = parse_message(req.message)
    except ParseError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Could not understand that message clearly ({e}). Try naming your area and how much water is left.",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    zone_name = facts.get("zone_name")
    if not zone_name:
        raise HTTPException(
            status_code=422,
            detail="Could not tell which area you mean. Please include your area name.",
        )

    tank_level = facts.get("tank_level_percent")
    if tank_level is None:
        raise HTTPException(
            status_code=422,
            detail="Could not tell how much water is left. Please say roughly how full the tank is.",
        )

    days = facts.get("days_since_delivery") or 0

    # --- decision made HERE, by the logic engine, not the LLM ---
    volunteer_facts = [
        Clause(Term("tank_level", (zone_name, tank_level))),
        Clause(Term("days_since_delivery", (zone_name, days))),
    ]
    engine = EntitlementEngine(ENTITLEMENT_RULES + volunteer_facts)
    entitled_results = engine.backward_chain(Term("entitled", (zone_name,)))
    priority_results = engine.backward_chain(Term("high_priority", (zone_name,)))

    entitled = bool(entitled_results)
    high_priority = bool(priority_results)
    proof_trace = ""
    if priority_results:
        proof_trace = priority_results[0][1].pretty()
    elif entitled_results:
        proof_trace = entitled_results[0][1].pretty()

    # --- LLM rewrites the engine's own trace, adding nothing ---
    try:
        explanation = explain_decision(zone_name, entitled, high_priority, proof_trace)
    except RuntimeError:
        explanation = proof_trace or "Not entitled under the current thresholds."

    estimated_slot = None
    problem, assignment = _state["problem"], _state["assignment"]
    if entitled and problem is not None and assignment is not None:
        for t in problem.tankers:
            for slot in range(problem.num_slots):
                if assignment.get((t.id, slot)) == zone_name:
                    estimated_slot = {"tanker_id": t.id, "slot": slot}
                    break
            if estimated_slot:
                break

    return {
        "understood": facts,
        "zone_name": zone_name,
        "entitled": entitled,
        "high_priority": high_priority,
        "explanation": explanation,
        "proof_trace": proof_trace,
        "estimated_slot": estimated_slot,
        "estimated_slot_note": None if estimated_slot else "Not yet scheduled today -- pending dispatch.",
    }


@app.get("/api/driver/routes/{tanker_id}")
def driver_routes(tanker_id: str):
    """
    Route list for one tanker: today's deliveries in slot order, each with
    the SHORTEST real road path (Phase 2's A* over the Chennai road graph)
    from its nearest source station to the zone -- the trip the driver
    actually makes after refilling.
    """
    problem, assignment = _state["problem"], _state["assignment"]
    if problem is None or assignment is None:
        raise HTTPException(status_code=400, detail="No schedule generated yet")

    valid_ids = {t.id for t in problem.tankers}
    if tanker_id not in valid_ids:
        raise HTTPException(status_code=404, detail=f"Unknown tanker '{tanker_id}'")

    deliveries = []
    for slot in range(problem.num_slots):
        zone_name = assignment.get((tanker_id, slot))
        if zone_name is None:
            continue

        zone = problem.zone_by_name(zone_name)
        station, route = nearest_station_to_zone(ROUTE_GEOMETRY, zone_name)

        deliveries.append(
            {
                "slot": slot,
                "zone_name": zone_name,
                "need_liters": zone.need_liters,
                "is_high_priority": zone.is_high_priority,
                "completed": (tanker_id, slot) in _state["completed"],
                "zone_coords": ZONE_COORDS.get(zone_name),
                "station_name": station,
                "station_coords": SOURCE_STATIONS.get(station) if station else None,
                "route_coords": route["coords"] if route else [],
                "distance_m": route["distance_m"] if route else None,
            }
        )

    return {"tanker_id": tanker_id, "deliveries": deliveries}


class CompleteRequest(BaseModel):
    tanker_id: str
    slot: int
    completed: bool = True


@app.post("/api/driver/complete")
def driver_complete(req: CompleteRequest):
    """
    Mark (or un-mark) one delivery as completed. This only sets a status
    flag -- the CSP assignment is untouched, so the dispatcher still sees
    what was planned next to what is done.
    """
    problem, assignment = _state["problem"], _state["assignment"]
    if problem is None or assignment is None:
        raise HTTPException(status_code=400, detail="No schedule generated yet")

    key = (req.tanker_id, req.slot)
    if assignment.get(key) is None:
        raise HTTPException(
            status_code=404, detail=f"No delivery scheduled for {req.tanker_id} slot {req.slot}"
        )

    if req.completed:
        _state["completed"].add(key)
    else:
        _state["completed"].discard(key)

    return {"tanker_id": req.tanker_id, "slot": req.slot, "completed": req.completed}


@app.get("/api/status")
def status():
    """
    Current schedule + completion flags. The dispatcher dashboard polls
    this so a driver's completion shows up within a few seconds.
    """
    problem, assignment = _state["problem"], _state["assignment"]
    if problem is None or assignment is None:
        return {"schedule": None}
    return _serialize_assignment(problem, assignment)


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
