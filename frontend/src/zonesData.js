// Mirrors phase2_routing/zones_data.py -- zone centers (real, geocoded) and
// source stations (SYNTHETIC, confirmed with project owner). Kept in sync
// by hand since the frontend has no Python import path; if Phase 2's
// coordinates change, update both.

export const ZONE_COORDS = {
  thiruvotriyur: [13.1718028, 80.3052689],
  manali: [13.1810602, 80.2694192],
  royapuram: [13.1042898, 80.2936125],
  teynampet: [13.0443237, 80.2498455],
  kodambakkam: [13.049207, 80.2242829],
  alandur: [13.0028216, 80.1719186],
  perungudi: [12.9710239, 80.2418051],
  tondiarpet: [13.1275202, 80.2819242],
};

// SYNTHETIC source stations -- not real Metrowater depot coordinates.
export const SOURCE_STATIONS = {
  station_a: [13.15, 80.29],
  station_b: [13.1, 80.28],
  station_c: [13.05, 80.24],
  station_d: [13.0, 80.2],
  station_e: [12.97, 80.24],
};

export const MAP_CENTER = [13.06, 80.25];
