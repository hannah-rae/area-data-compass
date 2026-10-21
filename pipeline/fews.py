"""FEWS NET projected acute food insecurity (latest outlook, ML2) joined to geoBoundaries units and project points."""
import sys, json, os, glob, collections, warnings, geopandas as gpd
warnings.filterwarnings("ignore")
D, OUT = sys.argv[1], sys.argv[2]
ne = gpd.read_file(f"{D}/ne50.geojson")
i3 = {r.ISO_A2_EH: (r.ISO_A3 if r.ISO_A3 != "-99" else r.ISO_A3_EH) for r in ne.itertuples()}
projects = json.load(open(f"{OUT}/projects_joined.json"))
res = {}
for f in sorted(glob.glob(f"{D}/fews/fews_*.json")):
    if os.path.getsize(f) < 10: continue
    cc = os.path.basename(f)[5:7]; iso = i3.get(cc)
    if not iso or not os.path.exists(f"{OUT}/geo/{iso}.json"): continue
    d = json.load(open(f)); last = max(x["reporting_date"] for x in d)
    rows = [x for x in d if x["reporting_date"] == last and x["scenario"] == "ML2" and x["value"]]
    if not rows: continue
    ph = {x["fnid"]: int(x["value"]) for x in rows}
    per = (rows[0]["projection_start"], rows[0]["projection_end"])
    doc = rows[0]["source_document"]
    gs = [g for g in glob.glob(f"{D}/fews/geo/{cc}_*.geojson") if os.path.getsize(g) > 1000]
    if not gs: print(iso, "no geometry"); continue
    feats = [f for g in gs for f in json.load(open(g))["features"] if f.get("geometry")]
    u = gpd.GeoDataFrame.from_features(feats, crs=4326)
    u = u[u["fnid"].isin(ph)].copy(); u["phase"] = u["fnid"].map(ph)
    u["geometry"] = u.geometry.buffer(0)
    if u.empty: print(iso, "no matching fnids"); continue
    def at_points(geoms):
        pts = gpd.GeoDataFrame(geometry=geoms, crs=4326)
        j = gpd.sjoin(pts, u[["phase", "geometry"]], how="left", predicate="within")
        j = j.groupby(level=0)["phase"].max()
        return [int(v) if v == v else None for v in j.reindex(range(len(pts))).values]
    out = {"period": per, "doc": doc, "reported": last}
    for L in ("ADM1", "ADM2"):
        p = f"{D}/gb/{iso}_{L}.geojson"
        if not os.path.exists(p) or os.path.getsize(p) < 200: continue
        g = gpd.read_file(p); g = g[g.geometry.notna() & ~g.geometry.is_empty].reset_index(drop=True)
        if L == "ADM1":
            # worst phase covering any part of the admin1, plus share of its area in Phase 3+
            ov = gpd.overlay(gpd.GeoDataFrame({"i": range(len(g))}, geometry=g.geometry.buffer(0), crs=4326), u[["phase", "geometry"]], how="intersection")
            ov["a"] = ov.to_crs(6933).area
            worst = ov.groupby("i")["phase"].max(); tot = ov.groupby("i")["a"].sum(); p3 = ov[ov.phase >= 3].groupby("i")["a"].sum()
            out["adm1"] = [[int(worst[i]) if i in worst else None, round(float(p3.get(i, 0) / tot[i] * 100)) if i in tot else None] for i in range(len(g))]
        else:
            out["adm2"] = at_points(g.geometry.representative_point())
    P = [p for p in projects if p["iso"] == iso]
    pp = at_points(gpd.points_from_xy([p["lon"] for p in P], [p["lat"] for p in P]))
    out["proj"] = {p["fid"]: v for p, v in zip(P, pp) if v}
    out["dist"] = dict(collections.Counter(int(v) for v in u.phase))
    res[iso] = out
    print(iso, per, out["dist"], len(out["proj"]), flush=True)
json.dump(res, open(f"{OUT}/fews.json", "w"))
