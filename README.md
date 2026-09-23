# Water Tanker Dispatch System

A decision-support system for municipal water tanker dispatch in Chennai.

Tankers are currently sent out by phone requests and local pressure, so some
areas get repeat deliveries while others wait days with no stated reason. This
system replaces that with a rule-based decision layer where every allocation is
**auditable** — you can ask why any zone did or didn't get water and get a
derivation, not an opinion.

Real geography (OpenStreetMap), synthetic operations data. It is a **validated
simulation**, not a live deployment.

---

## The architectural rule everything else follows

**The LLM never makes a decision.** It parses plain language into structured
facts and rephrases the logic engine's own proof into plain English. Entitlement
is decided by the logic engine; allocation by the CSP solver. Remove the LLM and
the system still works — it just loses its natural-language front door.

---

## What runs where

| Layer | Decides | Location |
|---|---|---|
| Entitlement engine | Which zones are entitled, and at what priority | `phase0_entitlement/` |
| CSP solver | Which tanker serves which zone, in which slot | `phase1_csp/` |
| Routing | Shortest road path between stations and zones | `phase2_routing/` |
| Repair | Smallest schedule change after a disruption | `phase3_repair/` |
| LLM layer | *Nothing* — parses input, explains output | `phase5_agentic/` |

Three user roles, each in its own folder:

| Role | What they do | Port |
|---|---|---|
| Dispatch officer | Generate the day's schedule, handle breakdowns and urgent requests | `frontend/` → 5173 |
| Ward volunteer | Report their area's water condition in plain language | `phase4_volunteer/` → 5175 |
| Tanker driver | Follow the route on a map, mark deliveries complete | `phase4_driver/` → 5176 |

---

## Setup

Requires Python 3.11 and Node.js.

```bash
pip install -r requirements.txt
npm install                        # root, for the run-everything script
npm install --prefix frontend
npm install --prefix phase4_volunteer
npm install --prefix phase4_driver
```

For the natural-language layer, copy `.env.example` to `.env` and add a free
[Groq](https://console.groq.com) API key:

```
GROQ_API_KEY=your_key_here
```

Everything except the volunteer chat works without a key.

---

## Running it

```bash
npm run dev
```

Starts all four servers with colour-coded output. `Ctrl+C` stops them all.

- Dispatcher dashboard — http://localhost:5173
- Volunteer chat — http://localhost:5175
- Driver route view — http://localhost:5176
- API — http://localhost:8000

On first run, Phase 2 downloads the Chennai road network from OpenStreetMap
(~2 min, ~85MB) and caches it. Subsequent starts are fast.

### A demo path that shows the whole system

1. **Dispatcher** → *Generate schedule*. The CSP solver allocates tankers to
   entitled zones.
2. **Volunteer** → type *"the tank in vadapalani is almost empty"*. The bot
   places Vadapalani in Zone 10 Kodambakkam (ward 130) from the zone data,
   reads the facts back, and waits for *Yes* before anything is decided. The
   logic engine then rules, and you get a plain-language answer plus a live
   status card. Expand *What I understood* to see the extracted facts and the
   raw proof tree — evidence the LLM didn't decide anything.
3. **Driver** → pick the tanker serving a zone, see the shortest road route
   drawn from its Metrowater filling point, tap *Mark delivered*.
4. **Dispatcher** → within ~3s that cell shows a green ✓. The volunteer's chat
   asks whether the water actually arrived.
5. **Dispatcher** → *Mark tanker unavailable*. Min-conflicts repairs the
   schedule and highlights only the cells that changed.

---

## Verifying the claims

```bash
python scripts/demo.py          # runs every claim below end to end
pytest                          # 155 tests across all phases
```

Individual pieces:

```bash
python phase0_entitlement/demo.py tondiarpet      # entitlement + proof tree
python phase0_entitlement/demo.py --all           # forward chaining
python phase1_csp/benchmark.py                    # heuristic benchmarks
python phase2_routing/visualize.py                # route map → route_map.html
python phase5_agentic/demo_partial_observability.py  # stale belief corrected
python phase6_polish/fairness_report.py           # fairness evidence
python phase6_polish/benchmark_report.py          # consolidated benchmarks
python scripts/build_metrowater_data.py           # rebuild + cross-check zone data
```

### Zone data

The 15 zones and their 200 divisions (wards) come from the Chennai Metrowater
zone map, transcribed in [data/metrowater/zones.csv](data/metrowater/zones.csv).
[data/metrowater/localities.csv](data/metrowater/localities.csv) places 487
named localities in their zone, using OpenStreetMap's official zone boundaries.
The build script refuses to write anything unless every OSM ward sits inside
the zone the Metrowater table assigns to it (196/196 agree; OSM lacks wards
151, 156, 194, 198 and 200).

A volunteer can name a zone, a locality, or a ward number. The lookup is a
table in `phase5_agentic/zone_registry.py`, not the LLM. A locality name used in
several zones ("Gandhi Nagar") gets a *which one?* question, never a guess.

### The fairness claim, measured

Under a deliberately strained fleet (2 tankers, 15 zones, 14 days):

| | Hard constraints only | + fairness soft constraint |
|---|---|---|
| Zones never served | **3** | **0** |
| Longest skip streak | **13 days** | **7 days** |
| Delivery spread | **3** | **1** |

The strained fleet is the point: with the full 5-tanker fleet, supply
(102,000L) far exceeds demand (56,000L), every zone is served every time, and
the fairness question never arises. Fairness is only testable when the
allocator must choose who waits.
---

## Design decisions worth defending

**Why the knowledge base is a text file.** `phase0_entitlement/knowledge_base.txt`
is parsed at runtime, not hardcoded. A reviewer can open it and check a rule
without reading Python.

**Why min-conflicts repairs instead of re-solving.** A dispatcher who has already
phoned five drivers cannot absorb a completely different schedule. Repair
produces a diff — what moved and why — not a fresh plan.

**Why hard constraints alone weren't enough.** An all-idle schedule satisfies
every hard constraint. Satisfaction search has no objective, so how many zones
get served is incidental to variable ordering. The soft constraint supplies the
objective, and degrades gracefully: when demand exceeds capacity it returns the
best partial schedule, where a hard "serve everyone" constraint would return
nothing.

**Why constraint (a) is weaker than it first looks.** It originally pruned any
zone whose need exceeded one tanker's capacity, which silently made a 10,000L
zone unservable by a 9,000L-only fleet — contradicting constraint (d), which
exists so several deliveries can accumulate. Need is met by the *sum* of
deliveries.

**Known limitation.** Tank levels, needs and the fleet are synthetic. The road
network, zone boundaries, localities, facility tags and filling points are real.
Filling points were geocoded from their published addresses: 11 to the street,
9 to the locality, 2 approximately (Thanikachalam Nagar, Pukraj Nagar; neither is
in OpenStreetMap). Southern Head Works has no address yet and is left out
rather than guessed.
