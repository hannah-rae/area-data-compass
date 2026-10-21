"""Country-level indicators: FAOSTAT, World Bank, INFORM, UNHCR, GDACS + area assignment."""
import sys, json, csv, collections, geopandas as gpd
D, OUT = sys.argv[1], sys.argv[2]
AREAS = {
 "africa": "AGO BDI BEN BFA BWA CIV CMR COD COG CPV ETH GHA GIN GMB KEN LBR LSO MDG MLI MOZ MUS MWI NAM NER NGA RWA SDN SEN SLE SOM SSD STP SWZ TGO TZA UGA ZAF ZMB ZWE",
 "asia": "AFG BGD IND IDN JPN KAZ KGZ KHM KOR LAO LKA MMR MNG MYS NPL PAK SGP THA TJK TKM TLS TWN UZB VNM HKG",
 "pacific": "AUS NZL PHL FJI FSM GUM KIR MHL MNP NRU PLW PNG PYF SLB TON VUT WSM COK",
 "caribbean": "BES BRB CUB CUW DOM GLP GRD HTI JAM LCA PRI TTO VCT GUY SUR",
 "latam": "ARG BLZ BOL BRA CHL COL CRI ECU GTM HND NIC PAN PER PRY SLV URY VEN",
 "europe": "ALB ARM AUT AZE BEL BGR BIH BLR CHE CYP CZE DEU DNK ESP EST FIN FRA GBR GEO GRC HRV HUN IRL ITA LTU LUX LVA MDA MKD MNE NLD NOR POL PRT ROU RUS SRB SVK SVN SWE TUR UKR XKX",
 "mideast": "EGY JOR LBN SYR YEM IRQ BHR MAR TUN",
 "namerica": "USA CAN MEX",
}
area_of = {i: a for a, s in AREAS.items() for i in s.split()}
projects = json.load(open(f"{OUT}/projects_joined.json"))
adm = json.load(open(f"{OUT}/admin_summary.json"))
isos = sorted(set(p["iso"] for p in projects))
miss = [i for i in isos if i not in area_of]; assert not miss, miss
ne = gpd.read_file(f"{D}/ne50.geojson"); ne["iso"] = ne["ISO_A3"].where(ne["ISO_A3"] != "-99", ne["ISO_A3_EH"])
m49 = {r.iso: str(r.ISO_N3).lstrip("0") for r in ne.itertuples() if r.ISO_N3 not in ("-99", None)}
m49.update({"PRI": "630", "GUM": "316", "MNP": "580", "PYF": "258", "COK": "184", "HKG": "344", "TWN": "158", "GLP": "312", "CUW": "531", "BES": "535", "XKX": "412"})
C = {}
names = {p["iso"]: p["country"] for p in projects}
for iso in isos:
    P = [p for p in projects if p["iso"] == iso]
    C[iso] = {"name": names[iso].strip(), "area": area_of[iso], **adm[iso], "n_proj": len(P),
              "groups": dict(collections.Counter(p["group"] for p in P))}
# FAOSTAT
items = {"210041": "pou", "210091": "fi_modsev", "21025": "stunting", "21026": "wasting", "21047": "water_basic",
         "21048": "sanit_basic", "21043": "anemia", "21035": "cereal_import_dep"}
back = {v: k for k, v in m49.items() if k in C}
fao = collections.defaultdict(lambda: collections.defaultdict(list))
with open(f"{D}/fs/Food_Security_Data_E_All_Data_(Normalized).csv", encoding="latin-1") as f:
    for r in csv.DictReader(f):
        iso = back.get(r["Area Code (M49)"].strip("'").lstrip("0"))
        if not iso or r["Item Code"] not in items or not r["Value"]: continue
        try: v = float(r["Value"].replace("<", "").strip())
        except ValueError: continue
        fao[iso][items[r["Item Code"]]].append([r["Year"], v, r["Value"].startswith("<")])
for iso in C:
    C[iso]["fao"] = {k: {"latest": sorted(s)[-1], "series": sorted(s)[-12:] if k == "pou" else None} for k, s in fao[iso].items()}
# World Bank
WB = {"SI.POV.DDAY": "poverty", "SH.STA.MMRT": "mmr", "SH.DYN.MORT": "u5mr", "SE.PRM.UNER.ZS": "out_of_school",
      "SL.UEM.1524.ZS": "youth_unemp", "EG.ELC.ACCS.ZS": "electricity", "SH.IMM.MEAS": "measles", "SP.POP.TOTL": "pop",
      "SE.SEC.CMPT.LO.ZS": "lsec_completion", "SL.UEM.NEET.ZS": "neet", "SP.RUR.TOTL.ZS": "rural"}
for code, key in WB.items():
    d = json.load(open(f"{D}/wb/{code}.json"))
    for r in d[1] or []:
        iso = r["countryiso3code"]
        if iso in C and r["value"] is not None: C[iso].setdefault("wb", {})[key] = [r["date"], round(r["value"], 1)]
# INFORM 2026
for ind, key in {"INFORM": "risk", "HA": "hazard", "VU": "vuln", "CC": "coping"}.items():
    for r in json.load(open(f"{D}/api/inform_{ind}.json")):
        iso = "XKX" if r["Iso3"] == "XKX" else r["Iso3"]
        if iso in C and r["IndicatorScore"] is not None: C[iso].setdefault("inform", {})[key] = r["IndicatorScore"]
# UNHCR 2025 (hosted = refugees + asylum seekers; idps; origin = refugees from this country)
num = lambda v: int(v) if str(v).lstrip("-").isdigit() else 0
for r in json.load(open(f"{D}/api/unhcr_coa.json"))["items"]:
    if r["coa_iso"] in C: C[r["coa_iso"]]["unhcr"] = {"hosted": num(r["refugees"]) + num(r["asylum_seekers"]), "idps": num(r["idps"]), "year": r["year"]}
for r in json.load(open(f"{D}/api/unhcr_coo.json"))["items"]:
    if r["coo_iso"] in C: C[r["coo_iso"]].setdefault("unhcr", {"year": r["year"]})["origin"] = num(r["refugees"]) + num(r["asylum_seekers"])
# GDACS orange/red alerts, last 30 days
for f in json.load(open(f"{D}/api/gdacs.json"))["features"]:
    p = f["properties"]
    ev = {"type": p["eventtype"], "level": p["alertlevel"], "name": p["name"], "from": p["fromdate"][:10], "to": p["todate"][:10],
          "url": p["url"]["report"], "sev": (p.get("severitydata") or {}).get("severitytext", "")}
    for a in p.get("affectedcountries") or []:
        if a["iso3"] in C: C[a["iso3"]].setdefault("gdacs", []).append(ev)
json.dump(C, open(f"{OUT}/countries.json", "w"))
print(len(C), collections.Counter(c["area"] for c in C.values()))
print({k: sum(1 for c in C.values() if k in c) for k in ("wb", "inform", "unhcr", "gdacs")}, sum(1 for c in C.values() if c["fao"]))
