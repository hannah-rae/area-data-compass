"""Admin1/admin2 rainfall stats (CHC SPI + CHIRPS-GEFS), simplified SVG paths, and project->district join."""
import sys, json, os, warnings, numpy as np, rasterio, geopandas as gpd
from rasterio import features
from rasterio.windows import from_bounds
from shapely.geometry import box, Polygon, MultiPolygon
warnings.filterwarnings("ignore")
D, OUT = sys.argv[1], sys.argv[2]
os.makedirs(f"{OUT}/geo", exist_ok=True)
spi = rasterio.open(f"{D}/SPI_18PentAccum_2026_p57_PRELIM.tif"); SPI = spi.read(1)
gef = rasterio.open(f"{D}/c3g_anom_2026.10.21.tif"); GEF = gef.read(1)
GEF = np.where(GEF < -9000, np.nan, GEF)
projects = json.load(open(f"{D}/projects.json"))
isos = sorted(set(p["iso"] for p in projects))
ne = gpd.read_file(f"{D}/ne50.geojson")
ne["iso"] = ne["ISO_A3"].where(ne["ISO_A3"] != "-99", ne["ISO_A3_EH"])

def load(iso, L):
    f = f"{D}/gb/{iso}_{L}.geojson"
    if not os.path.exists(f) or os.path.getsize(f) < 200: return None
    g = gpd.read_file(f)
    g = g[g.geometry.notna() & ~g.geometry.is_empty].copy()
    g["geometry"] = g.geometry.buffer(0)
    return g.reset_index(drop=True)

def zonal(g):
    """Return per-row (spi_mean, dry_pct, gefs_mean) via rasterize on the country window."""
    minx, miny, maxx, maxy = g.total_bounds
    minx, maxx = max(minx, -180), min(maxx, 180); miny, maxy = max(miny, -60), min(maxy, 60)
    n = len(g); res = [(None, None, None)] * n
    if miny >= maxy or minx >= maxx: return res
    win = from_bounds(minx - .05, miny - .05, maxx + .05, maxy + .05, spi.transform).round_offsets().round_lengths()
    tr = spi.window_transform(win)
    r0, c0 = int(win.row_off), int(win.col_off); h, w = int(win.height), int(win.width)
    r0c, c0c = max(r0, 0), max(c0, 0)
    a = SPI[r0c:r0 + h, c0c:c0 + w]; b = GEF[r0c:r0 + h, c0c:c0 + w]
    tr = spi.transform * rasterio.Affine.translation(c0c, r0c)
    ids = features.rasterize(((geom, i + 1) for i, geom in enumerate(g.geometry)), out_shape=a.shape, transform=tr, fill=0, dtype="int32")
    out = []
    for i in range(n):
        m = ids == i + 1
        if not m.any():  # tiny unit: sample the pixel under its representative point
            p = g.geometry.iloc[i].representative_point()
            rr, cc = rasterio.transform.rowcol(tr, p.x, p.y)
            if 0 <= rr < a.shape[0] and 0 <= cc < a.shape[1]:
                m = np.zeros(a.shape, bool); m[rr, cc] = True
        va = a[m]; va = va[np.isfinite(va) & (va > -50)]
        vb = b[m]; vb = vb[np.isfinite(vb)]
        out.append((round(float(va.mean()), 2) if va.size else None,
                    round(float((va <= -1).mean() * 100), 1) if va.size else None,
                    round(float(vb.mean()), 1) if vb.size else None))
    return out

def path(geom, tol):
    geom = geom.simplify(tol, preserve_topology=True)
    polys = geom.geoms if isinstance(geom, MultiPolygon) else [geom] if isinstance(geom, Polygon) else []
    s = []
    for p in polys:
        if p.area < (tol * tol) * 2: continue
        s.append("M" + "L".join(f"{x:.3f} {-y:.3f}" for x, y in p.exterior.coords[:-1]) + "Z")
    if not s and polys:  # keep at least the largest piece
        p = max(polys, key=lambda q: q.area)
        s.append("M" + "L".join(f"{x:.3f} {-y:.3f}" for x, y in p.exterior.coords[:-1]) + "Z")
    return "".join(s)

summary = {}
for iso in isos:
    P = [p for p in projects if p["iso"] == iso]
    a1, a2 = load(iso, "ADM1"), load(iso, "ADM2")
    if a1 is None:
        c = ne[ne.iso == iso]
        if not c.empty: a1 = gpd.GeoDataFrame({"shapeName": [c.NAME.values[0]]}, geometry=[c.geometry.values[0]], crs=4326)
        else:
            xs = [p["lon"] for p in P]; ys = [p["lat"] for p in P]
            a1 = gpd.GeoDataFrame({"shapeName": [P[0]["country"]]}, geometry=[box(min(xs) - .25, min(ys) - .25, max(xs) + .25, max(ys) + .25)], crs=4326)
    # Assign admin2 to admin1 by representative point
    if a2 is not None:
        rp = gpd.GeoDataFrame(geometry=a2.geometry.representative_point(), crs=4326)
        j = gpd.sjoin(rp, a1[["shapeName", "geometry"]], how="left", predicate="within")
        j = j[~j.index.duplicated()]
        a2["adm1"] = j["shapeName"].values
    minx, miny, maxx, maxy = a1.total_bounds
    ext = max(maxx - minx, maxy - miny)
    t1, t2 = ext / 450, ext / 700
    z1 = zonal(a1); z2 = zonal(a2) if a2 is not None else []
    adm1 = [{"n": r.shapeName, "d": path(r.geometry, t1), "spi": z[0], "dry": z[1], "gefs": z[2]} for r, z in zip(a1.itertuples(), z1)]
    adm2 = [{"n": r.shapeName, "p": (r.adm1 if isinstance(r.adm1, str) else None), "d": path(r.geometry, t2), "spi": z[0], "dry": z[1], "gefs": z[2]}
            for r, z in zip(a2.itertuples(), z2)] if a2 is not None else []
    # Projects -> admin1/admin2 (nearest unit when a point falls just outside, e.g. on the coast)
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy([p["lon"] for p in P], [p["lat"] for p in P]), crs=4326)
    fine = a2 if a2 is not None else a1
    k = gpd.sjoin_nearest(pts.to_crs(3857), fine[["geometry"]].to_crs(3857), how="left", max_distance=50000)
    k = k[~k.index.duplicated()]
    k1 = gpd.sjoin_nearest(pts.to_crs(3857), a1[["geometry"]].to_crs(3857), how="left", max_distance=50000)
    k1 = k1[~k1.index.duplicated()]
    for p, i2, i1 in zip(P, k["index_right"].values, k1["index_right"].values):
        p["a1"] = int(i1) if i1 == i1 else None
        p["a2"] = int(i2) if (a2 is not None and i2 == i2) else None
    for i, a in enumerate(adm1): a["np"] = sum(1 for p in P if p["a1"] == i)
    for i, a in enumerate(adm2): a["np"] = sum(1 for p in P if p["a2"] == i)
    json.dump({"iso": iso, "bbox": [round(float(v), 3) for v in a1.total_bounds], "adm1": adm1, "adm2": adm2}, open(f"{OUT}/geo/{iso}.json", "w"), separators=(",", ":"))
    # Country-level rainfall from all admin1 pixels combined
    cz = zonal(gpd.GeoDataFrame(geometry=[a1.unary_union], crs=4326))[0]
    summary[iso] = {"spi_mean": cz[0], "spi_dry_pct": cz[1], "gefs_anom_mm": cz[2], "n_adm1": len(adm1), "n_adm2": len(adm2),
                    "bbox": [round(float(v), 3) for v in a1.total_bounds]}
    print(iso, len(adm1), len(adm2), len(P), cz, os.path.getsize(f"{OUT}/geo/{iso}.json") // 1000, "KB", flush=True)
json.dump(summary, open(f"{OUT}/admin_summary.json", "w"))
json.dump(projects, open(f"{OUT}/projects_joined.json", "w"))
