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

from problem import build_problem, CSPProblem, Zone
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

# Standing facts about a zone (it hosts a school/clinic/hospital), as
# opposed to its CONDITION, which the volunteer reports. Taken from Phase
# 0's zone file so a volunteer's report is judged with the same facts the
# engine always had -- without them, a zone with a hospital could never be
# made high priority from the chat.
ZONE_FACTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "phase0_entitlement", "zone_reports.txt"
)
STANDING_ZONE_FACTS = [
    c for c in parse_kb(ZONE_FACTS_PATH) if c.head.predicate == "has_critical_facility"
]

# Need per delivery by priority -- the same values Phase 1's ZONES use.
NEED_HIGH_PRIORITY, NEED_NORMAL = 10000, 6000

# Phase 2 routing + Phase 5 LLM layer are appended to sys.path AFTER
# phase0's, so phase0's `parser` module keeps priority (phase2 has no
# module of that name, but the ordering makes the intent explicit).
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "phase2_routing"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "phase5_agentic"))

from route_geometry import build_route_geometry, nearest_station_to_zone  # noqa: E402
from zones_data import ZONE_COORDS, SOURCE_STATIONS, FILLING_POINT_NAMES  # noqa: E402

from conversation import (  # noqa: E402
    Session, COLLECTING, CONFIRMING, SUBMITTED, AWAITING_RECEIPT, CLOSED,
    ask_for_missing, confirmation_question, receipt_question, unknown_area_reply,
    ambiguous_area_question, zone_display, area_display,
)
from explain import explain_decision  # noqa: E402
from parsing import VALID_ZONES  # noqa: E402

# Route polylines are precomputed/cached by phase2 (real A* over the
# Chennai road graph) -- loading them here keeps the ~85MB graph out of
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
    # Matched as a regex rather than a fixed list: Vite silently moves to
    # the next free port when its default is taken (a stale dev server from
    # an earlier run is enough), and a UI on an unlisted port has every
    # request blocked by the browser -- which surfaces as "could not reach
    # the dispatch system" even though the backend is healthy. Any local
    # dev port is acceptable here; this is a local-only demo backend.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
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
        # Every zone can report; whether it is entitled is the engine's call.
        "zones": VALID_ZONES,
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
    session_id: str | None = None


# One conversation per volunteer, kept until the delivery is settled.
# A real deployment would persist these; this is a validated simulation
# (CLAUDE.md), so process memory is enough.
_sessions: dict = {}


def _get_session(session_id):
    if session_id and session_id in _sessions:
        return _sessions[session_id]
    session = Session()
    _sessions[session.session_id] = session
    return session


def _find_slot(zone_name: str):
    """Where the current schedule places this zone, if anywhere."""
    problem, assignment = _state["problem"], _state["assignment"]
    if problem is None or assignment is None:
        return None
    for t in problem.tankers:
        for slot in range(problem.num_slots):
            if assignment.get((t.id, slot)) == zone_name:
                return {"tanker_id": t.id, "slot": slot}
    return None


def _decide(facts: dict):
    """
    Ask Phase 0's engine to rule on these facts.

    RULE 2: the decision is made HERE, by backward chaining over the
    knowledge base -- never by the language model, which only produced the
    facts and will only rephrase the resulting proof.
    """
    zone_name = facts["zone_name"]
    volunteer_facts = [
        Clause(Term("tank_level", (zone_name, int(facts["tank_level_percent"])))),
        Clause(Term("days_since_delivery", (zone_name, int(facts.get("days_since_delivery") or 0)))),
    ]
    engine = EntitlementEngine(ENTITLEMENT_RULES + STANDING_ZONE_FACTS + volunteer_facts)
    entitled_results = engine.backward_chain(Term("entitled", (zone_name,)))
    priority_results = engine.backward_chain(Term("high_priority", (zone_name,)))

    entitled = bool(entitled_results)
    high_priority = bool(priority_results)
    if priority_results:
        proof_trace = priority_results[0][1].pretty()
    elif entitled_results:
        proof_trace = entitled_results[0][1].pretty()
    else:
        proof_trace = ""

    try:
        explanation = explain_decision(zone_display(zone_name), entitled, high_priority, proof_trace)
    except Exception:
        # Never let a language-model failure block a decision the engine
        # has already made -- fall back to the raw derivation.
        explanation = proof_trace or "Not entitled under the current thresholds."

    slot = None
    if entitled:
        slot = _find_slot(zone_name)
        if slot is None:
            slot = _insert_into_schedule(zone_name, high_priority)

    return {
        "zone_name": zone_name,
        "entitled": entitled,
        "high_priority": high_priority,
        "explanation": explanation,
        "proof_trace": proof_trace,
        "slot": slot,
    }


def _insert_into_schedule(zone_name: str, high_priority: bool):
    """
    Fit a newly-reported zone into today's schedule using Phase 3's
    min-conflicts repair -- the same "urgent request" path the dispatcher
    triggers manually.

    Without this an entitled volunteer report has nowhere to go: the zone
    is genuinely due water but absent from the schedule, so the status card
    would sit on "pending" indefinitely and the volunteer could never
    confirm receipt. Repair inserts it with the smallest change rather than
    re-solving the day, so deliveries already communicated to drivers stay
    put.

    If the zone was not entitled when the day was planned (say Anna Nagar,
    now reporting an empty tank), it is first ADDED to today's problem as a
    new domain value -- the engine has just ruled it entitled, so the CSP
    must be able to serve it. Its need follows the same priority rule as
    Phase 1's zones.

    Returns the assigned slot, or None if the zone cannot be fitted.
    """
    problem, assignment = _state["problem"], _state["assignment"]
    if problem is None or assignment is None:
        return None
    if zone_name not in {z.name for z in problem.zones}:
        _add_zone_to_problem(problem, zone_name, high_priority)

    broken = urgent_request(problem, assignment, zone_name)
    repaired, _diff, _steps = run_repair(
        problem, broken, seed=1, must_serve=frozenset({zone_name})
    )
    if repaired is None:
        return None

    _state["assignment"] = repaired
    return _find_slot(zone_name)


def _add_zone_to_problem(problem: CSPProblem, zone_name: str, high_priority: bool) -> None:
    """
    Make a newly-entitled zone a value the solver may assign.

    `problem.zones` is rebuilt rather than appended to: build_problem()
    hands out Phase 1's module-level ZONES list itself, so appending would
    silently change the zone set of every later problem too.
    """
    need = NEED_HIGH_PRIORITY if high_priority else NEED_NORMAL
    problem.zones = problem.zones + [Zone(zone_name, need, high_priority)]
    for var, domain in problem.domains.items():
        # A broken-down tanker's domain is just [None]; it stays unavailable.
        if domain != [None]:
            problem.domains[var] = [v for v in domain if v is not None] + [zone_name, None]


def _reply(session, text: str, **extra):
    session.remember("assistant", text)
    payload = {
        "session_id": session.session_id,
        "stage": session.stage,
        "reply": text,
        "facts": session.facts,
        "decision": session.decision,
    }
    payload.update(extra)
    return payload


def _ask_next(session) -> str:
    """
    The follow-up question when facts are still missing.

    Splits the one case the volunteer cannot recover from on their own: if
    they named a place that is not a served zone, re-asking "which area?"
    just loops, because the honest answer is that we do not cover it.
    """
    missing = session.missing_fields()
    facts = session.facts
    if "zone_name" in missing and facts.get("candidate_zones"):
        return ambiguous_area_question(facts["locality"], facts["candidate_zones"])
    place = facts.get("mentioned_place")
    if "zone_name" in missing and place:
        return unknown_area_reply(place, facts)
    return ask_for_missing(missing, facts)


@app.post("/api/volunteer/chat")
def volunteer_chat(req: ChatMessage):
    """
    One turn of a volunteer conversation.

    The dialogue accumulates facts across turns, reads them back for
    approval before any decision is made, then tracks the delivery until
    the volunteer confirms water actually arrived.

    RULE 2 BOUNDARY, unchanged: the LLM extracts facts and rephrases the
    engine's proof. Phase 0's engine decides entitlement; the CSP solver
    decides allocation. This endpoint only sequences the conversation.
    """
    from parsing import parse_in_context, interpret_yes_no, ParseError

    session = _get_session(req.session_id)
    message = req.message.strip()
    session.remember("user", message)

    # ---- awaiting confirmation that the delivery actually happened ----
    if session.stage == AWAITING_RECEIPT:
        answer = interpret_yes_no(message)
        if answer is True:
            session.delivery_confirmed = True
            session.stage = CLOSED
            return _reply(session, "Thank you for confirming \u2014 I have recorded that the "
                                   "water arrived. You can start a new report any time.")
        if answer is False:
            session.delivery_confirmed = False
            session.stage = CLOSED
            return _reply(session, "Thank you for telling us. I have recorded that the water "
                                   "did NOT arrive, so dispatch can follow it up. Please start "
                                   "a new report if you need water again.")
        return _reply(session, "Sorry, I did not catch that. Did the tanker arrive and fill "
                               "your tank? Please reply yes or no.")

    # ---- awaiting approval of the facts ----
    if session.stage == CONFIRMING:
        answer = interpret_yes_no(message)
        if answer is False:
            session.reset_facts()
            return _reply(session, "No problem \u2014 let us start again. Which area are you "
                                   "reporting for, and roughly how much water is left?")
        if answer is None:
            # Not a yes/no: treat it as a correction and re-read the facts.
            try:
                session.facts = parse_in_context(message, session.facts)
            except ParseError:
                return _reply(session, "Sorry, I did not catch that. Is the summary above "
                                       "correct? Please reply yes or no.")
            if session.has_enough():
                return _reply(session, confirmation_question(session.facts))
            return _reply(session, _ask_next(session))

        # Approved -> now, and only now, ask the engine.
        session.decision = _decide(session.facts)
        session.stage = SUBMITTED if session.decision["entitled"] else CLOSED
        return _reply(session, session.decision["explanation"])

    # ---- already submitted: keep the conversation useful ----
    if session.stage in (SUBMITTED, CLOSED):
        if session.stage == SUBMITTED:
            return _reply(session, "Your report is already in \u2014 you can see its status above. "
                                   "I will ask you to confirm once the driver marks it delivered.")
        return _reply(session, "That report is closed. Tell me your area and how much water is "
                               "left to start a new one.")

    # ---- collecting facts ----
    try:
        session.facts = parse_in_context(message, session.facts)
    except ParseError:
        return _reply(session, "Sorry, I did not quite follow that. Could you tell me your area "
                               "and roughly how much water is left \u2014 for example, \u201cthe tank in "
                               "Kodambakkam is almost empty\u201d?")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not session.has_enough():
        return _reply(session, _ask_next(session))

    session.stage = CONFIRMING
    return _reply(session, confirmation_question(session.facts))


@app.get("/api/volunteer/session/{session_id}")
def volunteer_session(session_id: str):
    """
    Live status for the card shown in the chat. Polled by the volunteer
    view so the schedule stays current, and so the volunteer is asked to
    confirm receipt as soon as the driver marks the delivery complete.
    """
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session")

    status = None
    if session.decision and session.decision["entitled"]:
        zone_name = session.decision["zone_name"]
        slot = session.decision.get("slot") or _find_slot(zone_name)
        # Keep the slot fresh: repair or a re-generate may have moved it.
        session.decision["slot"] = slot

        if session.stage == CLOSED:
            state = "confirmed" if session.delivery_confirmed else "not_received"
        elif slot is None:
            state = "pending"
        elif (slot["tanker_id"], slot["slot"]) in _state["completed"]:
            state = "delivered"
            if session.stage == SUBMITTED:
                session.stage = AWAITING_RECEIPT
                session.remember("assistant", receipt_question(zone_name))
        else:
            state = "scheduled"

        status = {
            "zone_name": zone_name,
            "area_label": area_display(session.facts),
            "high_priority": session.decision["high_priority"],
            "slot": slot,
            "state": state,
            "question": receipt_question(zone_name) if session.stage == AWAITING_RECEIPT else None,
        }

    return {
        "session_id": session.session_id,
        "stage": session.stage,
        "facts": session.facts,
        "decision": session.decision,
        "status": status,
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
                "zone_label": zone_display(zone_name),
                "station_name": station,
                "station_label": FILLING_POINT_NAMES.get(station, station),
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
