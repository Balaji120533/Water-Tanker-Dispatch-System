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
import threading
import time

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
from zone_registry import locality_point  # noqa: E402

# Filling point -> zone-centre routes, precomputed by phase2 (real A* over
# the Chennai road graph). Used when a delivery has no reported locality.
ROUTE_GEOMETRY = build_route_geometry()

# Routes to the exact place a volunteer reported ("Arumbakkam", not the
# centre of Zone 8) can't be precomputed, so the road graph is loaded here
# too -- on a background thread, so the API is usable at once and the
# planner simply becomes available a moment later.
_planner = {"planner": None, "error": None}


def _load_planner():
    try:
        from graph_loader import load_graph
        from dynamic_route import RoutePlanner
        _planner["planner"] = RoutePlanner(load_graph(), SOURCE_STATIONS)
    except Exception as e:  # routing to localities degrades to zone centres
        _planner["error"] = str(e)


threading.Thread(target=_load_planner, daemon=True).start()

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
        "requests": _serialize_requests(),
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
    # A new schedule reuses the same (tanker, slot) cells for different
    # zones, so yesterday's ticks would sit on today's deliveries.
    _state["completed"] = set()

    # Volunteer requests the engine already approved must survive a
    # regenerate -- otherwise planning the day after a report arrives would
    # silently drop it. Each missing zone is inserted by the same repair
    # path as when the report first came in.
    for session in _open_request_sessions():
        zone = session.decision["zone_name"]
        if _find_slot(zone) is None:
            _insert_into_schedule(zone, session.decision["high_priority"])
    solution = _state["assignment"]

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
    # Zones a volunteer has been told are coming must not be quietly
    # dropped by the repair. If the remaining fleet genuinely cannot cover
    # them all, fall back to the plain repair rather than failing outright;
    # those requests then show as "pending" rather than vanishing.
    promised = frozenset(s.decision["zone_name"] for s in _open_request_sessions())
    repaired, diff, steps = run_repair(problem, dict(broken), seed=1, must_serve=promised)
    if repaired is None and promised:
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


# --- volunteer requests on the map ------------------------------------
# A request is simply a chat session whose report the engine approved. The
# CSP allocates by zone; what a request adds is WHERE in the zone the
# water is needed, and the route there from the nearest filling point.

def _open_request_sessions() -> list:
    """Approved, entitled reports whose delivery hasn't happened yet."""
    return sorted(
        (s for s in _sessions.values()
         if s.decision and s.decision["entitled"] and s.stage == SUBMITTED),
        key=lambda s: s.created_at,
    )


def _request_point(session) -> tuple[list[float], str]:
    """The reported place, or the zone centre if only a zone/ward was given."""
    zone = session.decision["zone_name"]
    point = locality_point(session.facts.get("locality"), zone)
    if point is not None:
        return list(point), "locality"
    return list(ZONE_COORDS[zone]), "zone"


def _request_route(session) -> dict | None:
    """
    Nearest filling point by road to the reported place, and the route.
    Computed once per request and kept on the session. Before the road
    graph has loaded, falls back to the precomputed zone-centre route.
    """
    cached = session.decision.get("route")
    if cached and not cached.get("fallback"):
        return cached

    point, source = _request_point(session)
    planner = _planner["planner"]
    if planner is not None:
        found = planner.nearest_filling_point(*point)
        if found is not None:
            session.decision["route"] = {
                "station": found["station"], "distance_m": found["distance_m"],
                "coords": found["coords"], "fallback": False,
            }
            return session.decision["route"]

    station, route = nearest_station_to_zone(ROUTE_GEOMETRY, session.decision["zone_name"])
    if route is None:
        return None
    session.decision["route"] = {
        "station": station, "distance_m": route["distance_m"],
        "coords": route["coords"], "fallback": True,
    }
    return session.decision["route"]


def _request_state(session) -> tuple[str, dict | None]:
    """Where an approved request stands: pending / scheduled / delivered / ..."""
    zone = session.decision["zone_name"]
    if session.stage == CLOSED:
        return ("confirmed" if session.delivery_confirmed else "not_received"), session.decision.get("slot")
    if session.stage == AWAITING_RECEIPT:
        return "delivered", session.decision.get("slot")

    # Re-read every time: a repair or a regenerate may have moved it.
    slot = _find_slot(zone)
    session.decision["slot"] = slot
    if slot is None:
        return "pending", None
    if (slot["tanker_id"], slot["slot"]) in _state["completed"]:
        session.stage = AWAITING_RECEIPT
        session.remember("assistant", receipt_question(zone))
        return "delivered", slot
    return "scheduled", slot


def _serialize_requests() -> list[dict]:
    out = []
    for s in sorted(_sessions.values(), key=lambda s: s.created_at):
        if not (s.decision and s.decision["entitled"]):
            continue
        state, slot = _request_state(s)
        point, source = _request_point(s)
        route = _request_route(s) if state in ("pending", "scheduled") else s.decision.get("route")
        out.append({
            "id": s.session_id,
            "zone_name": s.decision["zone_name"],
            "zone_label": zone_display(s.decision["zone_name"]),
            "area_label": area_display(s.facts),
            "locality": s.facts.get("locality"),
            "point": point,
            "point_source": source,
            "tank_level_percent": s.facts.get("tank_level_percent"),
            "high_priority": s.decision["high_priority"],
            "state": state,
            "slot": slot,
            "station": route["station"] if route else None,
            "station_label": FILLING_POINT_NAMES.get(route["station"]) if route else None,
            "station_coords": SOURCE_STATIONS.get(route["station"]) if route else None,
            "route_coords": route["coords"] if route else [],
            "distance_m": route["distance_m"] if route else None,
            "route_to_zone_centre": bool(route and route.get("fallback")),
        })
    return out


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
        if session.decision["entitled"]:
            # Pin the reported place and find its nearest filling point now,
            # so the dispatcher's map shows it on the next poll.
            _request_route(session)
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
        state, slot = _request_state(session)
        route = session.decision.get("route")

        status = {
            "station_label": FILLING_POINT_NAMES.get(route["station"]) if route else None,
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

        # If a volunteer reported this zone, drive to the place they named
        # (the earliest open report), from its nearest filling point by road.
        # Otherwise, the precomputed route to the zone centre.
        request = next(
            (s for s in _open_request_sessions() if s.decision["zone_name"] == zone_name), None
        )
        if request is not None:
            route = _request_route(request)
            station = route["station"] if route else None
            target, _source = _request_point(request)
            drop_label = area_display(request.facts)
        else:
            station, route = nearest_station_to_zone(ROUTE_GEOMETRY, zone_name)
            target = ZONE_COORDS.get(zone_name)
            drop_label = zone_display(zone_name)

        deliveries.append(
            {
                "slot": slot,
                "zone_name": zone_name,
                "need_liters": zone.need_liters,
                "is_high_priority": zone.is_high_priority,
                "completed": (tanker_id, slot) in _state["completed"],
                "zone_coords": target,
                "zone_label": drop_label,
                "volunteer_request": request is not None,
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
        # Reports can arrive before the day is planned; show them anyway.
        return {"schedule": None, "requests": _serialize_requests()}
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
