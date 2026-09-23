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
  madhavaram: [13.1421473, 80.2323786],
  thiruvika_nagar: [13.1208988, 80.2295103],
  ambattur: [13.1055654, 80.1639586],
  anna_nagar: [13.088249, 80.2073398],
  valasaravakkam: [13.0415799, 80.1724952],
  adyar: [13.00645, 80.2577791],
  sozhanganallur: [12.8935, 80.2321],
};

// Zone number + name as printed on the Chennai Metrowater zone map
// (data/metrowater/zones.csv).
export const ZONE_LABELS = {
  thiruvotriyur: "Zone 1 Thiruvottiyur",
  manali: "Zone 2 Manali",
  madhavaram: "Zone 3 Madhavaram",
  tondiarpet: "Zone 4 Tondiarpet",
  royapuram: "Zone 5 Royapuram",
  thiruvika_nagar: "Zone 6 Thiru-Vi-Ka Nagar",
  ambattur: "Zone 7 Ambattur",
  anna_nagar: "Zone 8 Anna Nagar",
  teynampet: "Zone 9 Teynampet",
  kodambakkam: "Zone 10 Kodambakkam",
  valasaravakkam: "Zone 11 Valasaravakkam",
  alandur: "Zone 12 Alandur",
  adyar: "Zone 13 Adyar",
  perungudi: "Zone 14 Perungudi",
  sozhanganallur: "Zone 15 Shozhinganallur",
};

// Chennai Metrowater filling points (data/metrowater/filling_points.csv),
// geocoded from their published addresses. Regenerate from the CSV if it changes.
export const SOURCE_STATIONS = {
  fp_manali: [13.18106, 80.269419],
  fp_ernavoor: [13.1908163, 80.3040777],
  fp_ramasamy_nagar: [13.0258, 80.15857],
  fp_manali_new_town: [13.2116618, 80.2771598],
  fp_thanikachalam_nagar: [13.134332, 80.228224],
  fp_pukraj_nagar: [13.1421473, 80.2323786],
  fp_patel_nagar: [13.13907, 80.28203],
  fp_vyasarpadi: [13.1130472, 80.258722],
  fp_anna_poonga: [13.1122762, 80.2893812],
  fp_mogappair_west: [13.08221, 80.17041],
  fp_venkatapuram: [13.1175107, 80.152976],
  fp_kilpauk: [13.0870843, 80.2345901],
  fp_kk_nagar: [13.03849, 80.20173],
  fp_valasaravakkam: [13.0481004, 80.1829581],
  fp_alapakkam: [13.049901, 80.1654347],
  fp_nandambakkam: [13.01732, 80.19263],
  fp_pallipattu: [13.0027604, 80.2437561],
  fp_velachery: [12.9765177, 80.2197517],
  fp_ekkattuthangal: [13.0242453, 80.2065506],
  fp_mrc_nagar: [13.0209224, 80.2698276],
  fp_annai_therasa_nagar: [12.9691428, 80.2062626],
  fp_karapakkam: [12.9124767, 80.230128],
};

export const FILLING_POINT_NAMES = {
  fp_manali: "Manali Filling Point",
  fp_ernavoor: "Ernavoor Filling Point",
  fp_ramasamy_nagar: "Ramasamy Nagar Filling Point",
  fp_manali_new_town: "Manali New Town Filling Point",
  fp_thanikachalam_nagar: "Thanikachalam Nagar Filling Point",
  fp_pukraj_nagar: "Pukraj Nagar Filling Point",
  fp_patel_nagar: "Patel Nagar Filling Point",
  fp_vyasarpadi: "Vyasarpadi Filling Point",
  fp_anna_poonga: "Anna Poonga Filling Point",
  fp_mogappair_west: "Mogappair West Filling Point",
  fp_venkatapuram: "Venkatapuram Filling Point",
  fp_kilpauk: "Kilpauk Filling Point",
  fp_kk_nagar: "K.K.Nagar Filling Point",
  fp_valasaravakkam: "Valasaravakkam Filling Point",
  fp_alapakkam: "Alampakkam Filling Point",
  fp_nandambakkam: "Nandambakkam Filling Point",
  fp_pallipattu: "Pallipattu Filling Point",
  fp_velachery: "Velacheri Filling Point",
  fp_ekkattuthangal: "Ekkattuthangal Filling Point",
  fp_mrc_nagar: "MRC Nagar Filling Point",
  fp_annai_therasa_nagar: "Annai Therasa Nagar Filling Point",
  fp_karapakkam: "Karapakkam Filling Point",
};

export const MAP_CENTER = [13.05, 80.24];
