import sys, json, geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
D, OUT = sys.argv[1], sys.argv[2]
w = gpd.read_file(f"{D}/ne50.geojson")
w["iso"] = w["ISO_A3"].where(w["ISO_A3"] != "-99", w["ISO_A3_EH"])
w = w[w["CONTINENT"] != "Antarctica"]
paths = {}
def ring(r):
    pts = list(r.coords)
    return "M" + "L".join(f"{x:.1f} {-y:.1f}" for x, y in pts) + "Z"
for _, row in w.iterrows():
    g = row.geometry.simplify(0.15, preserve_topology=True)
    polys = g.geoms if isinstance(g, MultiPolygon) else [g]
    d = "".join(ring(p.exterior) for p in polys if p.area > 0.02 or row.iso in ("WSM","TON","KIR","BRB","VUT","SLB","JAM"))
    if d: paths[row.iso if row.iso != "-99" else row["ADM0_A3"]] = paths.get(row.iso, "") + d
json.dump(paths, open(OUT, "w"))
print(len(paths), sum(len(v) for v in paths.values()))
