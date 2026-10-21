import sys, csv, json, numpy as np, rasterio, geopandas as gpd
from rasterio.mask import mask
D = sys.argv[1]; OUT = sys.argv[2]
AREAS = {
 "africa": ["KEN","GHA","ZMB","GMB","LBR","TZA","UGA"],
 "asia": ["MMR","KHM","LKA","MNG","NPL"],
 "pacific": ["PHL","PNG","SLB","VUT","WSM","TON","KIR"],
 "caribbean": ["DOM","HTI","JAM","BRB"],
 "latam": ["GTM","HND","BOL","BRA","ARG","CHL"],
 "europe": ["UKR","TUR","ALB","GRC"],
 "mideast": ["EGY","SYR","YEM","LBN","JOR"],
 "namerica": ["MEX","USA","CAN"],
}
isos = [i for v in AREAS.values() for i in v]
w = gpd.read_file(f"{D}/ne50.geojson")
w["iso"] = w["ISO_A3"].where(w["ISO_A3"] != "-99", w["ISO_A3_EH"])
spi = rasterio.open(f"{D}/SPI_18PentAccum_2026_p57_PRELIM.tif")
gef = rasterio.open(f"{D}/c3g_anom_2026.10.21.tif")
res = {}
for iso in isos:
    row = w[w.iso == iso]
    if row.empty: print("missing", iso); continue
    g = row.geometry.values[0]; m49 = row["ISO_N3"].values[0]
    a, _ = mask(spi, [g], crop=True, all_touched=True, nodata=np.nan, filled=True)
    a = a[0]; v = a[np.isfinite(a) & (a > -50)]
    b, _ = mask(gef, [g], crop=True, all_touched=True, nodata=np.nan, filled=True)
    b = b[0]; u = b[np.isfinite(b) & (b > -9000)]
    res[iso] = dict(name=row["NAME"].values[0], m49=m49,
        lat=round(g.centroid.y, 2), lon=round(g.centroid.x, 2),
        spi_mean=round(float(v.mean()), 2) if v.size else None,
        spi_dry_pct=round(float((v <= -1).mean()*100), 1) if v.size else None,
        spi_wet_pct=round(float((v >= 1).mean()*100), 1) if v.size else None,
        gefs_anom_mm=round(float(u.mean()), 1) if u.size else None)
# FAO
items = {"210041":"pou","210091":"fi_modsev","21025":"stunting","21026":"wasting",
         "21047":"water_basic","21048":"sanit_basic","21043":"anemia","21035":"cereal_import_dep"}
m49map = {v["m49"].lstrip("0") if v["m49"] else None: k for k, v in res.items()}
fao = {k: {} for k in res}
with open(f"{D}/fs/Food_Security_Data_E_All_Data_(Normalized).csv", encoding="latin-1") as f:
    for r in csv.DictReader(f):
        code = r["Area Code (M49)"].strip("'").lstrip("0")
        iso = m49map.get(code)
        if not iso or r["Item Code"] not in items or r["Value"] in ("", None): continue
        key = items[r["Item Code"]]
        try: val = float(r["Value"].replace("<", "").strip())
        except ValueError: continue
        fao[iso].setdefault(key, []).append([r["Year"], val, r["Value"].startswith("<")])
for iso, d in fao.items():
    out = {}
    for k, ser in d.items():
        ser.sort(key=lambda x: x[0])
        out[k] = {"latest": ser[-1], "series": ser[-12:] if k == "pou" else None}
    res[iso]["fao"] = out
json.dump({"areas": AREAS, "countries": res}, open(OUT, "w"), indent=1)
for k, v in res.items(): print(k, v["name"], v["spi_mean"], v["spi_dry_pct"], v["gefs_anom_mm"], {a: b["latest"] for a, b in v.get("fao", {}).items() if a in ("pou","stunting")})
