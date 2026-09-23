/**
 * Builds the review presentation (CLAUDE.md Phase 6 deliverable).
 * Run: node scripts/build_slides.js
 */

const pptxgen = require("pptxgenjs");
const path = require("path");

const DEEP = "065A82";   // deep blue  -- dominant
const TEAL = "1C7293";   // teal       -- supporting
const MID = "21295C";    // midnight   -- dark backgrounds
const INK = "1A1A1A";
const MUTED = "5A6B78";
const LIGHT = "F4F7F9";
const WHITE = "FFFFFF";
const WARN = "C1443C";   // used only for the starvation figures
const GOOD = "2E7D5B";

const TITLE_FONT = "Cambria";
const BODY_FONT = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5
pres.author = "Balaji S";
pres.title = "Water Tanker Dispatch System";

// ---------- helpers ----------------------------------------------------

function darkSlide() {
  const s = pres.addSlide();
  s.background = { color: MID };
  return s;
}

function lightSlide(title, unit) {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  s.addText(title, {
    x: 0.6, y: 0.45, w: 10.2, h: 0.7,
    fontFace: TITLE_FONT, fontSize: 32, bold: true, color: INK,
    isTextBox: true, margin: 0,
  });
  if (unit) {
    s.addText(unit, {
      x: 11.0, y: 0.58, w: 1.8, h: 0.4,
      fontFace: BODY_FONT, fontSize: 12, bold: true, color: WHITE,
      align: "center", valign: "middle", isTextBox: true, margin: 0,
      fill: { color: TEAL }, shape: pres.ShapeType.roundRect, rectRadius: 0.1,
    });
  }
  return s;
}

/** Stat block: big number over a small label. */
function stat(slide, x, y, w, value, label, color) {
  slide.addText(value, {
    x, y, w, h: 0.85,
    fontFace: TITLE_FONT, fontSize: 48, bold: true, color: color || DEEP,
    align: "center", isTextBox: true, margin: 0,
  });
  slide.addText(label, {
    x, y: y + 0.85, w, h: 0.5,
    fontFace: BODY_FONT, fontSize: 12, color: MUTED,
    align: "center", isTextBox: true, margin: 0,
  });
}

/** Card with a tinted background -- no edge stripes. */
function card(slide, x, y, w, h, fill) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: fill || LIGHT }, line: { color: fill || LIGHT },
  });
}

function numberedStep(slide, x, y, w, n, heading, body) {
  slide.addShape(pres.ShapeType.ellipse, {
    x, y, w: 0.46, h: 0.46,
    fill: { color: DEEP }, line: { color: DEEP },
  });
  slide.addText(String(n), {
    x, y, w: 0.46, h: 0.46,
    fontFace: BODY_FONT, fontSize: 16, bold: true, color: WHITE,
    align: "center", valign: "middle", isTextBox: true, margin: 0,
  });
  slide.addText(heading, {
    x: x + 0.62, y: y - 0.02, w: w - 0.62, h: 0.32,
    fontFace: BODY_FONT, fontSize: 16, bold: true, color: INK,
    isTextBox: true, margin: 0,
  });
  slide.addText(body, {
    x: x + 0.62, y: y + 0.3, w: w - 0.62, h: 0.62,
    fontFace: BODY_FONT, fontSize: 13, color: MUTED,
    isTextBox: true, margin: 0,
  });
}

// ---------- 1. title ---------------------------------------------------
{
  const s = darkSlide();
  s.addText("Water Tanker Dispatch System", {
    x: 0.9, y: 2.25, w: 11.5, h: 1.0,
    fontFace: TITLE_FONT, fontSize: 44, bold: true, color: WHITE,
    isTextBox: true, margin: 0,
  });
  s.addText("Making municipal water allocation explainable, not just efficient", {
    x: 0.9, y: 3.3, w: 11.5, h: 0.5,
    fontFace: BODY_FONT, fontSize: 18, color: "BBD3E0",
    isTextBox: true, margin: 0,
  });
  s.addText("Chennai  ·  real roads and filling points, synthetic operations data  ·  a validated simulation", {
    x: 0.9, y: 4.6, w: 11.5, h: 0.4,
    fontFace: BODY_FONT, fontSize: 13, italic: true, color: "8FA8B8",
    isTextBox: true, margin: 0,
  });
  s.addNotes(
    "The framing to lead with: this is not a routing optimiser with a UI. " +
    "The problem is that water allocation currently has no stated reason behind it, " +
    "so the deliverable is an auditable decision, not merely a faster one."
  );
}

// ---------- 2. the problem ---------------------------------------------
{
  const s = lightSlide("The problem is accountability, not just efficiency");
  s.addText(
    "Tankers are dispatched by phone request and local pressure. Some areas get repeat " +
    "deliveries; others wait days.",
    { x: 0.6, y: 1.35, w: 12.1, h: 0.6, fontFace: BODY_FONT, fontSize: 16, color: INK, isTextBox: true, margin: 0 }
  );

  card(s, 0.6, 2.2, 5.9, 2.5);
  s.addText("What goes wrong", {
    x: 0.95, y: 2.45, w: 5.2, h: 0.35,
    fontFace: BODY_FONT, fontSize: 17, bold: true, color: DEEP, isTextBox: true, margin: 0,
  });
  s.addText([
    { text: "Allocation depends on who calls, not who needs", options: { bullet: true, breakLine: true } },
    { text: "No record of why a zone was skipped", options: { bullet: true, breakLine: true } },
    { text: "A resident asking “why not us?” gets no answer", options: { bullet: true } },
  ], { x: 0.95, y: 2.9, w: 5.2, h: 1.6, fontFace: BODY_FONT, fontSize: 14, color: INK, isTextBox: true, margin: 0, paraSpaceAfter: 8 });

  card(s, 6.8, 2.2, 5.9, 2.5, "E8F1F6");
  s.addText("What this system requires of itself", {
    x: 7.15, y: 2.45, w: 5.2, h: 0.35,
    fontFace: BODY_FONT, fontSize: 17, bold: true, color: DEEP, isTextBox: true, margin: 0,
  });
  s.addText([
    { text: "Every decision carries a derivation", options: { bullet: true, breakLine: true } },
    { text: "Thresholds are policy, set in a readable file", options: { bullet: true, breakLine: true } },
    { text: "No component may decide without showing why", options: { bullet: true } },
  ], { x: 7.15, y: 2.9, w: 5.2, h: 1.6, fontFace: BODY_FONT, fontSize: 14, color: INK, isTextBox: true, margin: 0, paraSpaceAfter: 8 });

  s.addText(
    "This rules out a learned model that outputs a schedule: it could reproduce historical " +
    "unfairness while making the reasoning opaque.",
    { x: 0.6, y: 5.05, w: 12.1, h: 0.5, fontFace: BODY_FONT, fontSize: 14, italic: true, color: MUTED, isTextBox: true, margin: 0 }
  );
  s.addNotes(
    "The key argument for the panel: why not just train a model? Because entitlement is a " +
    "normative policy, not a pattern. A classifier trained on past dispatch would learn the " +
    "existing bias and hide the reasoning."
  );
}

// ---------- 3. architecture --------------------------------------------
{
  const s = lightSlide("Four layers, one rule");

  const layers = [
    ["Entitlement engine", "Which zones qualify, at what priority", "First-order logic", "Unit IV"],
    ["CSP solver", "Which tanker serves which zone, when", "Constraint satisfaction", "Unit III"],
    ["Routing", "Shortest real road path", "A* informed search", "Unit II"],
    ["Repair", "Smallest change after a disruption", "Min-conflicts local search", "Unit III"],
  ];

  let y = 1.4;
  layers.forEach(([name, what, how, unit]) => {
    card(s, 0.6, y, 12.1, 0.82);
    s.addText(name, {
      x: 0.95, y: y + 0.1, w: 3.0, h: 0.32,
      fontFace: BODY_FONT, fontSize: 16, bold: true, color: INK, isTextBox: true, margin: 0,
    });
    s.addText(what, {
      x: 0.95, y: y + 0.44, w: 5.2, h: 0.3,
      fontFace: BODY_FONT, fontSize: 13, color: MUTED, isTextBox: true, margin: 0,
    });
    s.addText(how, {
      x: 6.4, y: y + 0.25, w: 4.2, h: 0.32,
      fontFace: BODY_FONT, fontSize: 14, color: DEEP, isTextBox: true, margin: 0,
    });
    s.addText(unit, {
      x: 11.1, y: y + 0.24, w: 1.3, h: 0.34,
      fontFace: BODY_FONT, fontSize: 12, bold: true, color: WHITE,
      align: "center", valign: "middle", isTextBox: true, margin: 0,
      fill: { color: TEAL }, shape: pres.ShapeType.roundRect, rectRadius: 0.08,
    });
    y += 0.95;
  });

  s.addShape(pres.ShapeType.roundRect, {
    x: 0.6, y: 5.35, w: 12.1, h: 0.85, rectRadius: 0.08,
    fill: { color: MID }, line: { color: MID },
  });
  s.addText("The LLM never makes a decision. It parses input into facts and rephrases the engine’s own proof.", {
    x: 0.95, y: 5.5, w: 11.4, h: 0.5,
    fontFace: BODY_FONT, fontSize: 16, bold: true, color: WHITE, isTextBox: true, margin: 0,
  });
  s.addNotes(
    "If asked what holds this together: remove the LLM and the system still works, it just " +
    "loses its natural-language front door. That is the test of whether the boundary is real."
  );
}

// ---------- 4. entitlement ---------------------------------------------
{
  const s = lightSlide("Entitlement: a decision you can check", "Unit IV");

  s.addText("The knowledge base is a text file, parsed at runtime — not hardcoded.", {
    x: 0.6, y: 1.3, w: 12.1, h: 0.4, fontFace: BODY_FONT, fontSize: 15, color: MUTED, isTextBox: true, margin: 0,
  });

  card(s, 0.6, 1.85, 6.0, 1.75, "EDF2F5");
  s.addText(
    "entitled(Zone) :-\n    tank_level(Zone, Level), lt30(Level).\n\n" +
    "high_priority(Zone) :-\n    entitled(Zone), has_critical_facility(Zone).",
    { x: 0.9, y: 2.05, w: 5.5, h: 1.4, fontFace: "Courier New", fontSize: 11, color: INK, isTextBox: true, margin: 0 }
  );

  card(s, 6.9, 1.85, 5.8, 1.75, "EDF2F5");
  s.addText(
    "entitled(tondiarpet)\n  tank_level(tondiarpet, 8)   [fact]\n  lt30(8)   [arithmetic]",
    { x: 7.2, y: 2.15, w: 5.2, h: 1.1, fontFace: "Courier New", fontSize: 11, color: INK, isTextBox: true, margin: 0 }
  );

  s.addText("Rules a reviewer can open and check", {
    x: 0.9, y: 3.65, w: 5.5, h: 0.3, fontFace: BODY_FONT, fontSize: 12, italic: true, color: MUTED, isTextBox: true, margin: 0,
  });
  s.addText("The proof returned with every verdict", {
    x: 7.2, y: 3.65, w: 5.2, h: 0.3, fontFace: BODY_FONT, fontSize: 12, italic: true, color: MUTED, isTextBox: true, margin: 0,
  });

  numberedStep(s, 0.6, 4.35, 4.0, 1, "Unification", "With occurs-check — correctness, not decoration");
  numberedStep(s, 4.7, 4.35, 4.0, 2, "Backward chaining", "Goal-driven; returns the proof tree");
  numberedStep(s, 8.8, 4.35, 3.9, 3, "Forward chaining", "Derives every entitled zone at once");

  s.addNotes(
    "Both chaining directions are implemented because they answer different questions: one " +
    "zone with a proof, versus all zones in a pass. A test asserts they agree, which " +
    "cross-validates the engine."
  );
}

// ---------- 5. CSP ------------------------------------------------------
{
  const s = lightSlide("Allocation as a constraint satisfaction problem", "Unit III");

  s.addText("Variables: (tanker, slot). Domain: entitled zones, or idle.", {
    x: 0.6, y: 1.3, w: 12.1, h: 0.35, fontFace: BODY_FONT, fontSize: 15, color: MUTED, isTextBox: true, margin: 0,
  });

  const cons = [
    ["(a)", "A tanker carries a usable load", "unary — domain pruning"],
    ["(b)", "Refill between deliveries", "binary — consecutive slots"],
    ["(c)", "No two tankers to one zone in a slot", "binary — across tankers"],
    ["(d)", "A zone is never supplied beyond its need", "n-ary — found by measurement"],
  ];
  let y = 1.85;
  cons.forEach(([tag, text, kind], i) => {
    card(s, 0.6, y, 12.1, 0.72, i === 3 ? "E8F1F6" : LIGHT);
    s.addText(tag, {
      x: 0.9, y: y + 0.19, w: 0.6, h: 0.34,
      fontFace: BODY_FONT, fontSize: 15, bold: true, color: DEEP, isTextBox: true, margin: 0,
    });
    s.addText(text, {
      x: 1.6, y: y + 0.19, w: 6.6, h: 0.34,
      fontFace: BODY_FONT, fontSize: 15, color: INK, isTextBox: true, margin: 0,
    });
    s.addText(kind, {
      x: 8.4, y: y + 0.21, w: 4.0, h: 0.32,
      fontFace: BODY_FONT, fontSize: 13, color: MUTED, isTextBox: true, margin: 0,
    });
    y += 0.82;
  });

  s.addText(
    "Constraint (d) was discovered, not designed. With only (a)–(c) the solver parked one zone " +
    "in every slot while seven entitled zones got nothing — perfectly valid, operationally useless.",
    { x: 0.6, y: 5.3, w: 12.1, h: 0.7, fontFace: BODY_FONT, fontSize: 14, italic: true, color: INK, isTextBox: true, margin: 0 }
  );

  s.addNotes(
    "Expect a question on how (d) was found. Answer: it only surfaced when the fairness study " +
    "counted outcomes over a fortnight. A constraint model can be internally consistent, fully " +
    "tested, and still encode the wrong problem."
  );
}

// ---------- 6. benchmark / negative finding -----------------------------
{
  const s = lightSlide("The heuristics did not help — and that is the finding", "Unit III");

  card(s, 0.6, 1.35, 5.9, 2.9);
  s.addText("Satisfaction search", {
    x: 0.95, y: 1.6, w: 5.2, h: 0.35, fontFace: BODY_FONT, fontSize: 17, bold: true, color: INK, isTextBox: true, margin: 0,
  });
  s.addText([
    { text: "Plain backtracking          16 nodes", options: { breakLine: true } },
    { text: "+ AC-3                      16 nodes", options: { breakLine: true } },
    { text: "+ MRV                       16 nodes", options: { breakLine: true } },
    { text: "+ degree                    16 nodes", options: { breakLine: true } },
    { text: "+ LCV                       16 nodes", options: {} },
  ], { x: 0.95, y: 2.05, w: 5.2, h: 1.5, fontFace: "Courier New", fontSize: 12, color: INK, isTextBox: true, margin: 0 });
  s.addText("An all-idle schedule satisfies every hard constraint, so the first path tried already succeeds. No dead end → nothing to prune.", {
    x: 0.95, y: 3.55, w: 5.2, h: 0.6, fontFace: BODY_FONT, fontSize: 12, color: MUTED, isTextBox: true, margin: 0,
  });

  card(s, 6.8, 1.35, 5.9, 2.9, "E8F1F6");
  s.addText("Optimisation search", {
    x: 7.15, y: 1.6, w: 5.2, h: 0.35, fontFace: BODY_FONT, fontSize: 17, bold: true, color: INK, isTextBox: true, margin: 0,
  });
  s.addText([
    { text: "Real    5 tankers    61 nodes   8/8 zones", options: { breakLine: true } },
    { text: "Strained 2 tankers 6,581 nodes  2/8 zones", options: { breakLine: true } },
    { text: "Large   5 slots      71 nodes   8/8 zones", options: {} },
  ], { x: 7.15, y: 2.05, w: 5.3, h: 1.1, fontFace: "Courier New", fontSize: 11, color: INK, isTextBox: true, margin: 0 });
  s.addText("Branch-and-bound cannot stop at the first valid leaf, so ordering and bounding genuinely matter — 6,581 nodes when the fleet is short.", {
    x: 7.15, y: 3.35, w: 5.2, h: 0.8, fontFace: BODY_FONT, fontSize: 12, color: MUTED, isTextBox: true, margin: 0,
  });

  s.addShape(pres.ShapeType.roundRect, {
    x: 0.6, y: 4.55, w: 12.1, h: 1.25, rectRadius: 0.08,
    fill: { color: MID }, line: { color: MID },
  });
  s.addText("Satisfaction search has no objective. How many zones get served is incidental to variable ordering — 8 under one ordering, 3 under another, with nothing preferring either. That is why a soft constraint was needed.", {
    x: 1.0, y: 4.75, w: 11.3, h: 0.9,
    fontFace: BODY_FONT, fontSize: 15, color: WHITE, isTextBox: true, margin: 0,
  });

  s.addNotes(
    "Do not apologise for the flat node counts. Explain the mechanism: heuristics pay off when " +
    "search must backtrack, and this instance never does. The interesting consequence is the " +
    "missing objective, which leads into the fairness slide."
  );
}

// ---------- 7. fairness -------------------------------------------------
{
  const s = lightSlide("Fairness, measured rather than asserted", "Unit III");

  s.addText("14 simulated days, 15 zones, a deliberately strained 2-tanker fleet.", {
    x: 0.6, y: 1.3, w: 12.1, h: 0.35, fontFace: BODY_FONT, fontSize: 15, color: MUTED, isTextBox: true, margin: 0,
  });

  card(s, 0.6, 1.9, 5.9, 2.7);
  s.addText("Hard constraints only", {
    x: 0.95, y: 2.1, w: 5.2, h: 0.35, fontFace: BODY_FONT, fontSize: 17, bold: true, color: INK, isTextBox: true, margin: 0,
  });
  stat(s, 0.95, 2.55, 1.7, "3", "zones never served", WARN);
  stat(s, 2.75, 2.55, 1.7, "13", "day skip streak", WARN);
  stat(s, 4.55, 2.55, 1.6, "3", "spread", WARN);

  card(s, 6.8, 1.9, 5.9, 2.7, "E8F1F6");
  s.addText("+ fairness soft constraint", {
    x: 7.15, y: 2.1, w: 5.2, h: 0.35, fontFace: BODY_FONT, fontSize: 17, bold: true, color: INK, isTextBox: true, margin: 0,
  });
  stat(s, 7.15, 2.55, 1.7, "0", "zones never served", GOOD);
  stat(s, 8.95, 2.55, 1.7, "7", "day skip streak", GOOD);
  stat(s, 10.75, 2.55, 1.6, "1", "spread", GOOD);

  s.addText(
    "Without the soft constraint, three zones received nothing in a fortnight — one was entitled " +
    "but skipped for thirteen consecutive days.",
    { x: 0.6, y: 4.8, w: 12.1, h: 0.5, fontFace: BODY_FONT, fontSize: 15, color: INK, isTextBox: true, margin: 0 }
  );
  s.addText(
    "Soft, not hard: a hard “serve everyone” constraint makes the CSP unsatisfiable exactly when " +
    "demand exceeds capacity — returning nothing on the days that matter most.",
    { x: 0.6, y: 5.35, w: 12.1, h: 0.55, fontFace: BODY_FONT, fontSize: 14, italic: true, color: MUTED, isTextBox: true, margin: 0 }
  );

  s.addNotes(
    "Anticipate: why strain the fleet? Because with 5 tankers, supply is 102,000 L against " +
    "56,000 L demand — everyone is served every time and there is nothing to be unfair about. " +
    "Fairness is only testable when the allocator must choose who waits."
  );
}

// ---------- 8. routing --------------------------------------------------
{
  const s = lightSlide("Routing over the real Chennai network", "Unit II");

  card(s, 0.6, 1.4, 3.85, 1.5);
  stat(s, 0.7, 1.55, 3.65, "95,457", "road nodes from OpenStreetMap");
  card(s, 4.75, 1.4, 3.8, 1.5);
  stat(s, 4.85, 1.55, 3.6, "240,062", "edges in the drive network");
  card(s, 8.85, 1.4, 3.85, 1.5);
  stat(s, 8.95, 1.55, 3.65, "0.000%", "drawn route vs A* distance", GOOD);

  s.addText("A* with a haversine heuristic, written from scratch", {
    x: 0.6, y: 3.15, w: 12.1, h: 0.4, fontFace: BODY_FONT, fontSize: 18, bold: true, color: INK, isTextBox: true, margin: 0,
  });
  s.addText(
    "Admissible because no road is shorter than the straight line between two points — so h(n) " +
    "never overestimates and A* returns an optimal path. A test asserts the cost matches Dijkstra exactly.",
    { x: 0.6, y: 3.6, w: 12.1, h: 0.6, fontFace: BODY_FONT, fontSize: 14, color: MUTED, isTextBox: true, margin: 0 }
  );

  card(s, 0.6, 4.4, 12.1, 1.5, "E8F1F6");
  s.addText("A geometry bug worth recording", {
    x: 0.95, y: 4.6, w: 11.4, h: 0.32, fontFace: BODY_FONT, fontSize: 16, bold: true, color: DEEP, isTextBox: true, margin: 0,
  });
  s.addText(
    "OSMnx places nodes only at intersections; a road’s curve lives on the edge. Drawing node-to-node " +
    "cut corners and appeared to cross buildings. After expanding each edge to its true shape, the drawn " +
    "polyline matches the A* road distance to 0.000% across all 330 routes — geometric proof it follows real roads.",
    { x: 0.95, y: 4.98, w: 11.4, h: 0.85, fontFace: BODY_FONT, fontSize: 13, color: INK, isTextBox: true, margin: 0 }
  );

  s.addNotes(
    "Good slide to show the live driver map on. The 0.000% figure is the defensible claim: it is " +
    "not 'it looks right', it is that the rendered line's length equals the search's cost."
  );
}

// ---------- 9. partial observability ------------------------------------
{
  const s = lightSlide("Planning on a belief, not on the truth", "Units I & II");

  s.addText("The system never reads a tank. It reads a report about a tank, which decays.", {
    x: 0.6, y: 1.3, w: 12.1, h: 0.4, fontFace: BODY_FONT, fontSize: 15, color: MUTED, isTextBox: true, margin: 0,
  });

  const rows = [
    ["t = 0 h", "45%", "45%", "not entitled", INK],
    ["t = 4 h", "45%  (stale)", "25%", "not entitled  ← wrong", WARN],
    ["t = 4 h  report arrives", "25%", "25%", "entitled", GOOD],
  ];
  s.addText(["Time", "Belief", "True level", "Decision from belief"].join("          "), {
    x: 0.95, y: 1.95, w: 11.4, h: 0.3, fontFace: BODY_FONT, fontSize: 12, bold: true, color: MUTED, isTextBox: true, margin: 0,
  });

  let y = 2.35;
  rows.forEach(([t, belief, truth, decision, color], i) => {
    card(s, 0.6, y, 12.1, 0.72, i === 2 ? "E8F1F6" : LIGHT);
    s.addText(t, { x: 0.95, y: y + 0.19, w: 3.0, h: 0.34, fontFace: BODY_FONT, fontSize: 14, color: INK, isTextBox: true, margin: 0 });
    s.addText(belief, { x: 4.1, y: y + 0.19, w: 2.2, h: 0.34, fontFace: BODY_FONT, fontSize: 14, color: INK, isTextBox: true, margin: 0 });
    s.addText(truth, { x: 6.4, y: y + 0.19, w: 2.2, h: 0.34, fontFace: BODY_FONT, fontSize: 14, color: INK, isTextBox: true, margin: 0 });
    s.addText(decision, { x: 8.7, y: y + 0.19, w: 3.7, h: 0.34, fontFace: BODY_FONT, fontSize: 14, bold: i !== 0, color, isTextBox: true, margin: 0 });
    y += 0.82;
  });

  s.addText(
    "At t = 4 h the belief is 20 points adrift and the system would have denied water to a zone that qualified.",
    { x: 0.6, y: 5.0, w: 12.1, h: 0.4, fontFace: BODY_FONT, fontSize: 15, color: INK, isTextBox: true, margin: 0 }
  );
  s.addText(
    "Any plan is optimal only for the belief that produced it. Since beliefs are stale by construction, " +
    "committing to one plan guarantees acting on outdated information — so the system replans.",
    { x: 0.6, y: 5.45, w: 12.1, h: 0.55, fontFace: BODY_FONT, fontSize: 14, italic: true, color: MUTED, isTextBox: true, margin: 0 }
  );

  s.addNotes(
    "The correction is not a patch applied to a plan — the decision is recomputed from the updated " +
    "belief. That distinction is what makes it online replanning rather than error handling."
  );
}

// ---------- 10. LLM boundary --------------------------------------------
{
  const s = lightSlide("Where the language model is allowed to act");

  numberedStep(s, 0.6, 1.5, 12.1, 1,
    "It extracts facts — and they are validated",
    "“the tank in Manali is empty”  →  { zone: manali, level: 0 }. Unknown zone, out-of-range value or malformed JSON is rejected, never guessed.");

  numberedStep(s, 0.6, 2.75, 12.1, 2,
    "The logic engine alone decides",
    "The model is never shown the entitlement rules and never asked for a verdict. Entitlement comes from backward chaining, allocation from the CSP solver.");

  numberedStep(s, 0.6, 4.0, 12.1, 3,
    "It rephrases the engine’s own proof",
    "Forbidden from adding, omitting or reversing any fact in the derivation it is given.");

  s.addShape(pres.ShapeType.roundRect, {
    x: 0.6, y: 5.3, w: 12.1, h: 0.9, rectRadius: 0.08,
    fill: { color: MID }, line: { color: MID },
  });
  s.addText("Remove the LLM and the system still works — it loses only its natural-language front door.", {
    x: 1.0, y: 5.5, w: 11.3, h: 0.5,
    fontFace: BODY_FONT, fontSize: 16, bold: true, color: WHITE, isTextBox: true, margin: 0,
  });

  s.addNotes(
    "This is the slide to be most precise on. The boundary is not a guideline in a prompt; " +
    "it is enforced by validation code between the model and the engine."
  );
}

// ---------- 11. syllabus mapping ----------------------------------------
{
  const s = lightSlide("Syllabus mapping");

  const map = [
    ["I", "Goal-based agent; partially observable environment", "partial_observability.py"],
    ["I", "Uninformed search baseline", "solver.py — plain backtracking"],
    ["II", "A* with haversine heuristic; admissibility", "astar.py"],
    ["II", "Local search — hill climbing, annealing", "sequencing.py"],
    ["II", "Online replanning on a belief state", "partial_observability.py"],
    ["III", "CSP; hard constraints (a)–(d)", "constraints.py"],
    ["III", "AC-3 constraint propagation", "ac3.py"],
    ["III", "MRV, degree, LCV", "heuristics.py"],
    ["III", "Min-conflicts repair", "min_conflicts.py"],
    ["III", "Soft constraints for fairness", "soft_constraints.py"],
    ["IV", "Unification with occurs-check", "unify.py"],
    ["IV", "Backward + forward chaining", "engine.py"],
  ];

  let y = 1.3;
  map.forEach(([unit, concept, file], i) => {
    if (i % 2 === 0) card(s, 0.6, y, 12.1, 0.42, "F7FAFB");
    s.addText(unit, {
      x: 0.8, y: y + 0.06, w: 0.5, h: 0.3,
      fontFace: BODY_FONT, fontSize: 12, bold: true, color: TEAL, isTextBox: true, margin: 0,
    });
    s.addText(concept, {
      x: 1.4, y: y + 0.06, w: 7.0, h: 0.3,
      fontFace: BODY_FONT, fontSize: 13, color: INK, isTextBox: true, margin: 0,
    });
    s.addText(file, {
      x: 8.5, y: y + 0.06, w: 4.0, h: 0.3,
      fontFace: "Courier New", fontSize: 11, color: MUTED, isTextBox: true, margin: 0,
    });
    y += 0.44;
  });

  s.addNotes("Every row is a file you can open on request. Nothing here is aspirational.");
}

// ---------- 12. results / close -----------------------------------------
{
  const s = darkSlide();
  s.addText("Where it stands", {
    x: 0.9, y: 0.7, w: 11.5, h: 0.7,
    fontFace: TITLE_FONT, fontSize: 34, bold: true, color: WHITE, isTextBox: true, margin: 0,
  });

  const facts = [
    ["162", "automated tests passing"],
    ["8 / 8", "entitled zones served, 61 nodes"],
    ["3 → 0", "starved zones under strain"],
    ["0.000%", "route drawing error"],
  ];
  let x = 0.9;
  facts.forEach(([v, l]) => {
    s.addText(v, {
      x, y: 1.75, w: 2.9, h: 0.8,
      fontFace: TITLE_FONT, fontSize: 40, bold: true, color: WHITE,
      align: "center", isTextBox: true, margin: 0,
    });
    s.addText(l, {
      x, y: 2.55, w: 2.9, h: 0.5,
      fontFace: BODY_FONT, fontSize: 12, color: "9FBCCC",
      align: "center", isTextBox: true, margin: 0,
    });
    x += 3.05;
  });

  s.addText("Honest scope", {
    x: 0.9, y: 3.5, w: 11.5, h: 0.4,
    fontFace: BODY_FONT, fontSize: 18, bold: true, color: WHITE, isTextBox: true, margin: 0,
  });
  s.addText([
    { text: "Road network, zone boundaries and filling points are real; tank levels and fleet are synthetic", options: { bullet: true, breakLine: true } },
    { text: "Refill is modelled as an idle slot, not computed from station travel time", options: { bullet: true, breakLine: true } },
    { text: "Benchmarks cover small instances; scaling beyond ~20 zones is untested", options: { bullet: true } },
  ], {
    x: 0.9, y: 3.95, w: 11.5, h: 1.5,
    fontFace: BODY_FONT, fontSize: 14, color: "C5D8E4", isTextBox: true, margin: 0, paraSpaceAfter: 8,
  });

  s.addText("python scripts/demo.py     ·     npm run dev", {
    x: 0.9, y: 5.75, w: 11.5, h: 0.4,
    fontFace: "Courier New", fontSize: 14, color: "7FA8BE", isTextBox: true, margin: 0,
  });

  s.addNotes(
    "Close on the limitations slide deliberately — stating scope precisely is more convincing " +
    "than claiming more than was built. Offer to run the demo script live."
  );
}

const out = path.join(__dirname, "..", "PRESENTATION.pptx");
pres.writeFile({ fileName: out }).then(() => console.log("wrote " + out));
