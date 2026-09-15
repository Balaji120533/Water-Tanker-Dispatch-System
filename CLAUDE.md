# CLAUDE.md — Water Tanker Dispatch System

> This file is read by Claude Code at the start of every session. It defines
> what we are building, the rules of engagement, and the phase-by-phase plan.
> Read it fully before writing any code.

---

## PROJECT SUMMARY

A decision-support system for municipal water tanker dispatch in Chennai.
Tankers are currently sent out by phone requests and local pressure, so some
areas get repeat deliveries while others wait days with no stated reason.

This system replaces that with a rule-based decision layer:
1. Decides **which zones are entitled to water and in what priority** (logic)
2. Assigns **tankers to zones** under capacity/refill/fairness constraints (CSP)
3. Routes tankers over the **real Chennai road network** under uncertainty (search)
4. Explains every decision so allocation is **auditable**

Three user roles: **dispatch officer** (primary), **ward volunteer** (submits
requests), **tanker driver** (executes routes).

This is an academic AI project mapping to four syllabus units. Real geography,
synthetic operations data. It is a **validated simulation**, not a live deployment.

---

## SYLLABUS MAPPING (keep every unit load-bearing)

- **Unit I** — Agent/environment framing (goal-based agent; stochastic, dynamic,
  partially observable env); uninformed search baseline.
- **Unit II** — A* routing with haversine heuristic; local search (hill climbing /
  simulated annealing) for route ordering; nondeterministic actions (AND-OR
  planning for breakdowns); partially observable env; online replanning.
- **Unit III** — CSP for tanker→zone allocation; AC-3 constraint propagation;
  backtracking with MRV / degree / LCV; min-conflicts local search for repair;
  soft constraints for weekly fairness.
- **Unit IV** — First-order logic entitlement rules; backward chaining (why a zone
  got priority); forward chaining (derive all entitled zones); resolution
  (definite non-entitlement vs. missing data); unification.

---

## RULES OF ENGAGEMENT (do not violate)

1. **You write the algorithms. Then, at the end of each phase, you TEACH me the
   ones you added.** Write clean, working implementations of every algorithm
   (unification, chaining, AC-3, backtracking, A*, local search, min-conflicts,
   etc.), plus all the UI, glue, simulator, and boilerplate. But you are NOT done
   with a phase until you have run the TEACH-BACK PROTOCOL below for every core
   algorithm that phase introduced. I am building this to learn and to defend it
   in interviews and reviews, so a working phase I don't understand is a failed
   phase.

2. **The LLM never makes a decision.** It parses input into facts and explains
   output in plain language. Entitlement is decided by the logic engine;
   allocation by the CSP solver. Never let the LLM assign a tanker or decide a
   priority. This separation is the whole architecture.

3. **One constraint at a time.** Never add multiple constraints at once. Add one,
   write a test proving it holds, commit, then add the next. The classic failure
   here is an unsatisfiable problem with no idea which rule caused it.

4. **Keep the solver a pure module.** No web code, no LLM calls inside the solver.
   It takes structured input and returns structured output. This separation is
   testable and is itself part of the architecture I present.

5. **Start small, scale later.** First versions run on tiny instances (5 tankers,
   10 zones). Prove correctness before scaling to realistic sizes.

6. **When you need data or a real-world value I have not provided, STOP and ASK
   me to fill it in.** Do not invent plausible-looking real data (real ward
   names, real station coordinates, real fleet sizes) silently. See the
   DATA I MUST PROVIDE section — every item there is something you must prompt
   me for when the phase needs it.

---

## TEACH-BACK PROTOCOL (run at the END of every phase)

After a phase's code works, for EACH core algorithm that phase introduced, do all
five of these before we move on. Keep it concrete — always tie the explanation to
the actual water-tanker code you just wrote, not a textbook abstraction.

1. **Plain-English idea** — what the algorithm does and the problem it solves, in
   2–4 sentences. No jargon until it's earned.
2. **Line-by-line walkthrough** — open the file you wrote and explain the key
   functions, with attention to the non-obvious lines (the occurs-check, the AC-3
   queue, the MRV selection, the heuristic). Point at the real variables.
3. **Trace one example** — pick a real input from our data (e.g. Kolathur at 15%)
   and trace the algorithm's execution step by step, showing how it reaches the
   answer. For search, show the nodes expanded; for chaining, show the proof tree.
4. **Why this algorithm, not another** — the design justification an examiner asks:
   why backtracking not brute force, why A* not BFS, why min-conflicts for repair
   not a full re-solve. State the trade-off explicitly.
---

## TECH STACK (all free tier, no paid keys)

- **Python 3.11** — logic engine, CSP solver, routing (written from scratch, then taught back)
- **OSMnx + NetworkX** — pull Chennai road network from OpenStreetMap
- **FastAPI** — thin backend API
- **SQLite** — storage (upgrade to Postgres only if genuinely needed)
- **React + Leaflet + Tailwind** — dispatcher map dashboard
- **Google Gemini / Groq free tier** — LLM parsing + explanation (Ollama local as fallback)
- **Render + Vercel free tier** — hosting

---

## DATA I MUST PROVIDE (Claude Code: prompt me for each when its phase arrives)

Some of these are free and real (you fetch them); some do not exist publicly and
I must supply synthetic values. For the ones marked **[ASK ME]**, pause and ask me
to fill in the value before proceeding — do not guess.

### Real, you fetch (free)
- **Chennai road network** — via OSMnx `graph_from_place("Chennai, India", network_type="drive")`. You handle this.
- **Critical facilities** — schools (`amenity=school`), clinics/hospitals
  (`amenity=clinic`/`hospital`) via OSMnx tags. You handle this.

### [ASK ME] — I must provide these (not publicly published)
- **[ASK ME] Ward / zone list** — which localities the demo covers. I'll give you
  a starting set (e.g. Kolathur, Anna Nagar West, Ambattur…). Ask me for the list
  and roughly how many zones (start ~10).
- **[ASK ME] Water source station locations** — lat/long of filling stations, or
  ask me to place ~15 plausible points. Metrowater publishes some; confirm with me
  which to use or whether to synthesise.
- **[ASK ME] Tanker fleet** — number of tankers and capacities (e.g. 12 tankers,
  mix of 9,000L and 12,000L). Not published — ask me for the values.
- **[ASK ME] Entitlement rules** — the actual FOL rules and thresholds (what tank %
  triggers entitlement, what makes a zone high-priority). I'll define these with
  you in Phase 0. Ask me before hardcoding any threshold.
- **[ASK ME] Ward boundary data** — if we show ward polygons, confirm the source
  (OSM boundaries or data.gov.in) and that boundaries are current. Ask me.
- **[ASK ME] LLM API key** — when we reach the LLM layer, ask me which provider
  (Gemini / Groq / Ollama) and remind me to add my key to a `.env` file. Never
  hardcode a key.

### Useful links to give me when relevant
- OpenStreetMap / OSMnx docs — for the road graph
- Metrowater public info — for realistic station/norm context (I verify currency)
- NBTC/entitlement norms — only if I want to ground rules in a real published norm

---

## PHASE-BY-PHASE PLAN

> Each phase is independently demoable. If time runs out after any phase, what
> exists is still a complete, defensible piece. Do phases in order.

---

### PHASE 0 — Entitlement Engine (Review 1 target)

**Goal:** Given a zone's reported condition, decide entitlement and priority, and
print the derivation (proof tree).

**Prompt to use:**
```
We're starting Phase 0 of the water tanker project (see CLAUDE.md).
Before any code: ASK ME for the initial zone list and the entitlement rules /
thresholds — do not invent them.

Then build, in Python from scratch (you write it, clean and commented):
1. A representation for FOL facts and definite clauses.
2. Unification with occurs-check.
3. Backward chaining that returns not just true/false but the proof tree.
4. Forward chaining to derive all entitled zones from a set of facts.

Keep the knowledge base in a readable text file (not hardcoded in Python) so a
reviewer can open it and check a rule. Add tests. Give me a terminal demo:
input a zone's condition, print the priority decision and the derivation.

THEN run the TEACH-BACK PROTOCOL (see CLAUDE.md) for: unification, backward
chaining, forward chaining. This phase is not done until you have.
```

**Deliverables:** problem statement, FOL knowledge base file, working
unification + chaining, derivation output, tests.

---

### PHASE 1 — CSP Allocation

**Goal:** Assign tankers to zones respecting hard constraints, prioritised by
Phase 0's output.

**Prompt to use:**
```
Phase 1 (see CLAUDE.md). ASK ME for the tanker fleet (count + capacities) and
confirm the zone set before coding.

Build the CSP solver in Python (you write it, clean and commented):
- Variables: (tanker, time-slot). Domains: zones.
- Hard constraints, added ONE AT A TIME with a test each:
  (a) tanker capacity covers zone need
  (b) refill at a source station between deliveries
  (c) no tanker double-booked in a slot
- AC-3 constraint propagation.
- Backtracking with MRV, then add degree heuristic, then LCV.
Keep a benchmark log: nodes explored and solve time, before vs after each
heuristic. Start at 5 tankers / 10 zones. Do NOT scale until it's correct.
The solver must be a pure module — no web/LLM code inside it.

THEN run the TEACH-BACK PROTOCOL for: AC-3, backtracking, and each heuristic
(MRV, degree, LCV). Use the benchmark numbers when you explain why the heuristics
help. This phase is not done until you have.
```

**Deliverables:** working CSP solver, per-heuristic benchmark table, tests.

---

### PHASE 2 — Routing on the Real Map

**Goal:** Route tankers over the real Chennai network; sequence each tanker's day.

**Prompt to use:**
```
Phase 2 (see CLAUDE.md). You handle OSMnx: pull the Chennai drive network and
the school/clinic facility tags. ASK ME to confirm/adjust the source-station
coordinates before wiring them in.

Then (you write it, clean and commented):
- A custom A* with a haversine heuristic over the road graph. Use this rather
  than only NetworkX shortest_path so I can present my own implementation.
- Compute travel times between source stations and zones.
- Sequence each tanker's deliveries for the day; improve the ordering with hill
  climbing / simulated annealing.
Show routes on a simple map output so I can eyeball correctness.

THEN run the TEACH-BACK PROTOCOL for: A* (and the haversine heuristic — cover
admissibility), and the local search used for ordering. This phase is not done
until you have.
```

**Deliverables:** A* routing on real roads, route sequencing, visual check.

---

### PHASE 3 — Repair + Dispatcher Dashboard (Review 2 target)

**Goal:** The live demo — generate, disrupt, repair — with a real UI.

**Prompt to use:**
```
Phase 3 (see CLAUDE.md). Two parts:

1. Min-conflicts local search for REPAIR (you write it, clean and commented):
   - "tanker breaks down" -> smallest change that restores a valid schedule
   - "urgent request inserted" -> smallest insertion
   Output a DIFF (what moved and why), not a fresh schedule.

2. Dispatcher dashboard (you build this fully — React + Leaflet + Tailwind):
   - Map with tankers, zones, source stations
   - Schedule table for the day
   - "Mark tanker unavailable" button -> triggers repair -> animates changed cells
   - FastAPI backend wrapping the solver (solver stays pure).

THEN run the TEACH-BACK PROTOCOL for min-conflicts local search — especially WHY
repair-in-place beats re-solving from scratch here. (The dashboard is UI, no
teach-back needed.) This phase is not done until you have.
```

**Deliverables:** working repair, live dispatcher demo of generate→disrupt→repair.

---

### PHASE 4 — Volunteer + Driver Views

**Goal:** Close the loop with the other two roles.

**Prompt to use:**
```
Phase 4 (see CLAUDE.md). Build (you can do these fully):
- Volunteer view: simple form / text input to report a zone's condition;
  returns priority + reason + estimated slot. Keep it dead simple.
- Driver view: stripped-down route list for one tanker, mark-delivery-complete
  buttons. Minimal on purpose.
Build the volunteer view first; the driver view is the one we cut if time is short.
```

**Deliverables:** volunteer request flow, driver route view.

---

### PHASE 5 — Agentic Layer + Partial Observability (Final Review target)

**Goal:** Natural-language in/out, and genuine planning under uncertainty.

**Prompt to use:**
```
Phase 5 (see CLAUDE.md). ASK ME which LLM provider (Gemini / Groq / Ollama) and
remind me to put the key in .env — never hardcode it.

1. LLM layer (you build, strict boundary from CLAUDE.md rule 2):
   - Parse a volunteer's plain Tamil/English message into structured facts.
   - Generate a plain-language explanation of an allocation decision, including
     WHY a zone was or wasn't prioritised (read it from the derivation).
   - The LLM must output structured JSON for facts; validate before use.

2. Partial-observability simulator (you build):
   - Tank levels drift over time; reports arrive stale.
   - The system plans on last-reported belief and REPLANS as new reports land
     (online search). Show a run where a stale belief is corrected mid-day.

THEN run the TEACH-BACK PROTOCOL for the online-search / belief-update loop (and
AND-OR contingency planning if you implemented it): what "planning on a belief"
means here and why replanning beats committing to one plan. The LLM layer is not
an algorithm — no teach-back for it, but restate its hard boundary (rule 2) in one
line. This phase is not done until you have.
```

**Deliverables:** NL parsing + explanation, belief-based replanning demo.

---

### PHASE 6 — Polish (Final Review)

**Prompt to use:**
```
Phase 6 (see CLAUDE.md). Help me produce:
- The benchmark tables (search nodes with/without heuristics).
- A FAIRNESS metric across a simulated week: show no zone is repeatedly skipped
  (this makes the fairness claim measurable, not asserted).
- Report + slide content mapping each component to its syllabus unit.
- A clean README and a reproducible demo script.
```

**Deliverables:** benchmarks, fairness evidence, report, slides, README.

---

## WHAT TO SAY IF I DRIFT

- If I try to move to the next phase before you've run the TEACH-BACK PROTOCOL on
  the current phase's algorithms, stop me — remind me of Rule 1. A working phase I
  can't explain is a failed phase. (I can say "skip teaching" to override, and you
  note it, but you don't skip it on your own.)
- If I try to add several constraints at once, remind me of Rule 3.
- If I try to let the LLM decide a priority or allocation, remind me of Rule 2.
- If during teach-back I answer a quiz question wrong, don't wave it through —
  correct me and re-ask a variant until it's right.