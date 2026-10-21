"""Package everything for the page: data.js (embedded) + geo/{ISO}.json (lazy-loaded per country)."""
import sys, json, os, re, glob, statistics
OUT, SITE, WORLD = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(f"{SITE}/geo", exist_ok=True)
C = json.load(open(f"{OUT}/countries.json"))
P = json.load(open(f"{OUT}/projects_joined.json"))
F = json.load(open(f"{OUT}/fews.json")) if os.path.exists(f"{OUT}/fews.json") else {}
NUM = re.compile(r"(-?\d+\.?\d*) (-?\d+\.?\d*)")
# Countries that straddle the antimeridian: move the minority side across so the map is contiguous.
EAST = {"FJI", "KIR", "NZL", "RUS", "TUV"}  # push western (negative) longitudes to +360
WEST = {"USA"}                               # pull far-eastern (Aleutian) longitudes to -360
def fix_lon(iso, x):
    if iso in EAST and x < 0: return x + 360
    if iso in WEST and x > 0: return x - 360
    return x
def fix_path(iso, d):
    if iso not in EAST | WEST: return d
    return NUM.sub(lambda m: f"{fix_lon(iso, float(m.group(1))):.3f} {m.group(2)}", d)
def bbox_of(d):
    xs, ys = [], []
    for m in NUM.finditer(d): xs.append(float(m.group(1))); ys.append(-float(m.group(2)))
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None
for p in P: p["lon"] = fix_lon(p["iso"], p["lon"])
groups = sorted(set(p["group"] for p in P)); summ = sorted(set(p["summary"] for p in P))
gi = {g: i for i, g in enumerate(groups)}; si = {s: i for i, s in enumerate(summ)}
for iso in C:
    g = json.load(open(f"{OUT}/geo/{iso}.json"))
    for a in g["adm1"] + g["adm2"]: a["d"] = fix_path(iso, a["d"])
    # Main view: admin1 units near the median centre (keeps e.g. overseas territories from shrinking the map)
    bbs = [bbox_of(a["d"]) for a in g["adm1"]]; ok = [b for b in bbs if b]
    cx = statistics.median((b[0] + b[2]) / 2 for b in ok); cy = statistics.median((b[1] + b[3]) / 2 for b in ok)
    near = [b for b in ok if abs((b[0] + b[2]) / 2 - cx) < 30 and abs((b[1] + b[3]) / 2 - cy) < 22] or ok
    view = [min(b[0] for b in near), min(b[1] for b in near), max(b[2] for b in near), max(b[3] for b in near)]
    f = F.get(iso)
    if f:
        for i, a in enumerate(g["adm1"]):
            if "adm1" in f and i < len(f["adm1"]): a["fp"], a["p3"] = f["adm1"][i]
        for i, a in enumerate(g["adm2"]):
            if "adm2" in f and i < len(f["adm2"]): a["fp"] = f["adm2"][i]
        C[iso]["fews"] = {"period": f["period"], "reported": f["reported"], "dist": f["dist"]}
    g["view"] = [round(v, 3) for v in view]
    C[iso]["view"] = g["view"]
    json.dump(g, open(f"{SITE}/geo/{iso}.json", "w"), separators=(",", ":"))
proj = []
for p in P:
    fp = F.get(p["iso"], {}).get("proj", {}).get(str(p["fid"]))
    proj.append([p["iso"], round(p["lon"], 3), round(p["lat"], 3), p["city"], gi[p["group"]], p["date"], si[p["summary"]], p["a1"], p["a2"], fp])
world = json.load(open(WORLD))
data = {"countries": C, "groups": groups, "summaries": summ, "projects": proj, "world": world}
s = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
open(f"{SITE}/data.json", "w").write(s)
print("data.json", len(s) // 1000, "KB; geo total", sum(os.path.getsize(x) for x in glob.glob(f"{SITE}/geo/*.json")) // 1000, "KB")
print("biggest geo:", sorted(((os.path.getsize(x) // 1000, os.path.basename(x)) for x in glob.glob(f"{SITE}/geo/*.json")))[-5:])
