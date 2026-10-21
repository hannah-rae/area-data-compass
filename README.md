# Area Data Compass

A prototype dashboard for humanitarian area leaders of The Church of Jesus Christ of Latter-day Saints. It shows open data on food security, water, health, education, disasters, and poverty next to the Church's 2025 humanitarian projects, so leaders can see where needs are growing, whether current projects reach those places, and which data sources to follow during the year.

Built as a discussion prototype for the AI for Social Innovation conference at BYU. Numbers are a snapshot from 21 October 2026.

**Live site:** `https://<your-github-user>.github.io/<repo-name>/` (after enabling GitHub Pages, see below)

## How to use it

1. **Choose your area and a topic.** Topics with a ★ are the area's 2025 priorities from the Caring Report.
2. **Compare countries.** The map and table show the topic's key numbers for every country with 2025 projects.
3. **Look inside a country.** Key takeaways, district maps (rain, 15-day forecast, FEWS NET food insecurity outlook), provinces vs. projects, and the data sources behind each number.

## Repository layout

| Path | What it is |
|---|---|
| `docs/` | The published site. `index.html` has all country data embedded; `geo/{ISO3}.json` holds each country's province/district boundaries and stats, loaded when a country is selected. |
| `pipeline/` | Python scripts that rebuild the data, plus the page template. |
| `archive/v1/` | The first mockup (sample countries only). |

## Data sources

| Data | Source | Level |
|---|---|---|
| 2025 project locations, types, summaries | [Caring Report 2025 map](https://church-gis.maps.arcgis.com/apps/instant/sidebar/index.html?appid=988483579f6944b2bcfc728fe5d35627) (public ArcGIS layer) | Point |
| Area priorities | [Caring for Those in Need: 2025 Report](https://www.churchofjesuschrist.org/serve/caring/report?lang=eng), area pages | Area |
| Rain, last 3 months (SPI) | UCSB Climate Hazards Center, CHIRPS3 SPI, 18-pentad, preliminary | ~5 km → district |
| 15-day rain forecast | UCSB CHC, CHIRPS-GEFS 15-day anomaly | ~5 km → district |
| Food insecurity outlook | FEWS NET Data Warehouse, Sept 2026 outlook (Oct 2026 – Jan 2027) | District × livelihood zone |
| Hunger, nutrition, water & sanitation | FAOSTAT Suite of Food Security Indicators | National |
| Poverty, health, schooling, jobs | World Bank World Development Indicators | National |
| Crisis risk | INFORM Risk Index 2026 (EC JRC) | National |
| Displacement | UNHCR Refugee Population Statistics (2025) | National |
| Disaster alerts | GDACS orange/red alerts, 21 Sep – 21 Oct 2026 | Event |
| Boundaries | [geoBoundaries](https://www.geoboundaries.org) ADM1/ADM2 (CC BY 4.0); Natural Earth 1:50m | Province, district |

Countries are assigned to the report's eight areas by geography, because the project layer has no area field. Coverage badges for data sources that are not connected live are approximate.

## Rebuilding the data

Requires Python 3.10+ with `geopandas`, `rasterio`, `numpy`, and `pandas`.

1. Download the inputs into `downloads/`:
   - `SPI_18PentAccum_2026_p57_PRELIM.tif` from `https://data.chc.ucsb.edu/products/SPI/CHIRPS3/18_pentad/prelim/`
   - `c3g_anom_2026.10.21.tif` from `https://data.chc.ucsb.edu/products/CHIRPS-GEFS/v3/15_day/global/anom/2026/`
   - FAOSTAT bulk file `Food_Security_Data_E_All_Data_(Normalized).zip`, unzipped to `downloads/fs/`
   - `ne50.geojson`: Natural Earth `ne_50m_admin_0_countries.geojson`
   - `projects_0.json`, `projects_1999.json`: the Caring Report layer, queried with `outSR=4326` (it returns 1,999 records per page)
   - `gb/{ISO3}_ADM1.geojson`, `gb/{ISO3}_ADM2.geojson`: geoBoundaries simplified boundaries
   - `wb/{indicator}.json`, `api/inform_*.json`, `api/unhcr_*.json`, `api/gdacs.json`: World Bank, INFORM, UNHCR, and GDACS API responses
   - `fews/fews_{ISO2}.json` (FEWS NET `ipcphase` with `start_date`) and `fews/geo/{ISO2}_{unit_type}.geojson` (FEWS NET `feature`)
2. Run the pipeline:

```bash
python pipeline/projects.py downloads
python pipeline/admin.py downloads build
python pipeline/country.py downloads build
python pipeline/fews.py downloads build
python pipeline/finalize.py build docs pipeline/map.json
python pipeline/assemble.py
```

To change only the page (layout, text, logic), edit `pipeline/template.html` and run `python pipeline/assemble.py`. This needs `docs/data.json` from step 2.

## Previewing locally

The page loads boundary files with `fetch`, so open it through a local web server rather than as a file:

```bash
python3 -m http.server 8000 --directory docs
```

Then open http://localhost:8000.
