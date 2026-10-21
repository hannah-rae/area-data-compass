import sys, json, geopandas as gpd
D = sys.argv[1]
FIX = {"Iraq": "IRQ", "Lao": "LAO", "The Gambia": "GMB", "Türkiye": "TUR", "Bonaire": "BES", "Curacao": "CUW",
 "Micronesia": "FSM", "Côte d'Ivoire": "CIV", "Republic of the Congo": "COG", "Democratic Republic of the Congo": "COD",
 "Hong Kong": "HKG", "Taiwan": "TWN", "South Korea": "KOR", "Russia": "RUS", "Kosovo": "XKX", "Guadeloupe": "GLP",
 "French Polynesia": "PYF", "Cook Islands": "COK", "Northern Mariana Islands": "MNP", "Guam": "GUM", "Puerto Rico": "PRI",
 "Eswatini": "SWZ", "Cabo Verde": "CPV", "Czechia": "CZE", "United States": "USA", "Bosnia and Herzegovina": "BIH",
 "Dominican Republic": "DOM", "Marshall Islands": "MHL", "Solomon Islands": "SLB", "North Macedonia": "MKD",
 "Saint Vincent and the Grenadines": "VCT", "Sao Tome and Principe": "STP", "South Sudan": "SSD", "Timor-Leste": "TLS",
 "Trinidad and Tobago": "TTO", "Vietnam": "VNM", "Syria": "SYR", "Tanzania": "TZA", "Moldova": "MDA", "Bolivia": "BOL",
 "Venezuela": "VEN", "Central African Republic": "CAF", "Saint Lucia": "LCA"}
w = gpd.read_file(f"{D}/ne50.geojson")
by = {}
for _, r in w.iterrows():
    iso = r.ISO_A3 if r.ISO_A3 != "-99" else r.ISO_A3_EH
    for n in (r.NAME, r.NAME_LONG, r.ADMIN, r.NAME_EN): by[str(n)] = iso
feats = []
for f in ("projects_0.json", "projects_1999.json"): feats += json.load(open(f"{D}/{f}"))["features"]
out, miss = [], set()
for f in feats:
    a = f["attributes"]; c = a["Country"].strip()
    iso = FIX.get(c) or by.get(c)
    if not iso or iso == "-99": miss.add(c); continue
    g = f.get("geometry") or {}
    out.append({"iso": iso, "country": c, "city": (a["City"] or "").strip(), "group": (a["ProjectGroup"] or "").strip(),
                "date": a["ImplementationStartDate"], "summary": (a["ProjectSummary"] or "").strip(),
                "lon": round(g.get("x", 0), 4) if g else None, "lat": round(g.get("y", 0), 4) if g else None, "fid": a["FID"]})
print(len(feats), len(out), "missing:", miss)
print("no geom:", sum(1 for p in out if p["lon"] is None))
json.dump(out, open(f"{D}/projects.json", "w"))
print(" ".join(sorted(set(p["iso"] for p in out))))
