# Spatial Hot Spot Analysis of Educational Facilities in Mandalay District

**Method:** Getis-Ord Gi* Local Spatial Statistic
**Dataset:** Humanitarian OpenStreetMap Team (HOTOSM) — Myanmar Education Facilities
**Study Area:** Mandalay District, Mandalay Region, Myanmar
**Date:** March 2026

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Background & Objectives](#2-background--objectives)
3. [Data Source](#3-data-source)
4. [Project Structure](#4-project-structure)
5. [Methodology](#5-methodology)
   - 5.1 [Study Area Definition](#51-study-area-definition)
   - 5.2 [Coordinate Reference Systems](#52-coordinate-reference-systems)
   - 5.3 [Fishnet Grid Construction](#53-fishnet-grid-construction)
   - 5.4 [Spatial Weights Matrix](#54-spatial-weights-matrix)
   - 5.5 [Getis-Ord Gi* Statistic](#55-getis-ord-gi-statistic)
   - 5.6 [Significance Classification](#56-significance-classification)
6. [Software & Dependencies](#6-software--dependencies)
7. [Installation](#7-installation)
8. [Running the Analysis](#8-running-the-analysis)
9. [Results & Findings](#9-results--findings)
10. [Output Files](#10-output-files)
11. [Web Map](#11-web-map)
12. [Limitations & Caveats](#12-limitations--caveats)
13. [Colour Scheme Reference](#13-colour-scheme-reference)
14. [References](#14-references)

---

## 1. Project Overview

This project performs a **spatial hot spot analysis** to identify statistically significant geographic clusters of high and low concentrations of educational facilities within Mandalay District, Myanmar. Using the **Getis-Ord Gi\*** local spatial statistic, the analysis determines not just where facilities are concentrated, but whether those concentrations are statistically meaningful relative to random chance — with inference controlled at three confidence levels (90%, 95%, 99%).

The results are delivered in two forms:
- A **static 5-panel analytical map** (PNG) suitable for reports
- A **fully interactive web map** (self-contained HTML) for exploration

---

## 2. Background & Objectives

Mandalay District is one of seven districts in Mandalay Region, central Myanmar. It encompasses the historic city of Mandalay and surrounding townships, including Aungmyethazan, Chanayethazan, Mahaaungmye, Chanmyathazi, Pyigyidagun, Patheingyi, Amarapura, and Tada-U. As the second-largest urban centre in Myanmar, the district exhibits substantial spatial heterogeneity in urban density, infrastructure, and service provision.

Understanding the **spatial distribution of educational facilities** is critical for:

- **Policy planning** — identifying underserved areas for new school placement
- **Equity analysis** — revealing urban–rural disparities in educational access
- **Infrastructure investment** — guiding resource allocation decisions
- **Academic research** — contributing to spatial analysis of public service provision

Simple visualisation of point locations fails to distinguish genuine geographic clusters from random dispersion. The Getis-Ord Gi* statistic addresses this by computing a formal spatial test at each location, accounting for the values of neighbouring locations and their spatial configuration.

---

## 3. Data Source

| Attribute      | Detail |
|---|---|
| **Name**       | HOTOSM Myanmar Education Facilities Points |
| **File**       | `hotosm_mmr_education_facilities_points_geojson.geojson` |
| **Provider**   | Humanitarian OpenStreetMap Team (HOTOSM) |
| **Coverage**   | Nationwide Myanmar |
| **Format**     | GeoJSON (FeatureCollection, Point geometry) |
| **CRS**        | WGS 84 (EPSG:4326) |
| **Total features** | 4,532 |
| **Encoding**   | UTF-8 |

### Attribute Schema

| Field | Type | Description |
|---|---|---|
| `name` | String | Burmese name of the facility (may be null) |
| `name:en` | String | English name (may be null) |
| `amenity` | String | OSM amenity tag: `school`, `university`, `college`, `kindergarten` |
| `building` | String | Building type (largely null) |
| `operator:type` | String | Operator type, e.g. `public` (largely null) |
| `capacity:persons` | Integer | Capacity (largely null) |
| `addr:full` | String | Full address (largely null) |
| `addr:city` | String | City/township name |
| `source` | String | Data source (largely null) |
| `name:my` | String | Myanmar-script name |
| `osm_id` | Integer | OpenStreetMap node ID |
| `osm_type` | String | OSM element type (`nodes`) |

### Mandalay District Subset

After geographic clipping, **180 facilities** were retained:

| Amenity Type | Count |
|---|---|
| school | 167 |
| university | 9 |
| kindergarten | 3 |
| college | 1 |
| **Total** | **180** |

---

## 4. Project Structure

```
demo/
├── hotosm_mmr_education_facilities_points_geojson.geojson   # Raw input data (4,532 features)
├── hotspot_analysis.py                                       # Main analysis script
├── build_webmap.py                                           # Web map builder script
├── mandalay_hotspot_results.geojson                          # Analysis output (8,690 grid cells)
├── mandalay_hotspot_analysis.png                             # Static 5-panel map (180 dpi)
├── mandalay_hotspot_webmap.html                              # Interactive web map (self-contained)
└── README.md                                                 # This file
```

### Script Responsibilities

| Script | Role |
|---|---|
| `hotspot_analysis.py` | Data loading, spatial filtering, grid creation, spatial weights, Gi* computation, significance classification, static map generation, GeoJSON export |
| `build_webmap.py` | Reads output GeoJSON, minifies coordinates, computes summary statistics, generates and writes the self-contained HTML web map |

---

## 5. Methodology

### 5.1 Study Area Definition

Mandalay District was delineated using an **approximate bounding box** derived from its known geographic extent:

```
Longitude: 95.85° E  to  96.45° E
Latitude:  21.70° N  to  22.20° N
```

All point features falling within this bounding box were retained. While an administrative boundary polygon would be more precise, the bounding-box approach is appropriate here because HOTOSM data does not include a district identifier field, and the bounding box captures all major townships of the district without external data dependencies.

### 5.2 Coordinate Reference Systems

| Stage | CRS | EPSG |
|---|---|---|
| Input data | WGS 84 (geographic) | 4326 |
| Grid construction & Gi* computation | WGS 84 / UTM Zone 47N (metric) | 32647 |
| Output GeoJSON & web map | WGS 84 (geographic) | 4326 |

Reprojection to **UTM Zone 47N** (EPSG:32647) ensures that grid cells and distance thresholds are defined in true metres rather than degrees, which is essential for correct spatial weight computation.

### 5.3 Fishnet Grid Construction

The study area is divided into a regular **fishnet (raster-like) grid** of square cells, each measuring **500 m × 500 m**. This areal unit approach converts the raw point pattern into a continuous field that can be subjected to spatial autocorrelation testing.

**Construction steps:**

1. Compute the bounding envelope of all retained points in UTM coordinates.
2. Generate arrays of X and Y breakpoints at 500 m intervals using `numpy.arange`.
3. Construct a `shapely.geometry.box` polygon for each cell.
4. Assemble cells into a `GeoDataFrame` with row/column indices and centroid coordinates.
5. Perform a **spatial join** (`gpd.sjoin`, predicate `within`) to count how many facility points fall inside each cell.
6. Cells outside the study area bounding box are removed via `gpd.overlay` intersection.

**Grid statistics:**

| Metric | Value |
|---|---|
| Total cells | 8,690 |
| Cells with ≥ 1 facility | 130 (1.5%) |
| Maximum facilities per cell | 6 |
| Mean count (occupied cells only) | 1.37 |

The choice of 500 m cells represents a practical balance:
- Small enough to resolve intra-urban variation across Mandalay's township grid (~1 km blocks)
- Large enough that most cells capture at least one nearby facility in dense areas
- Consistent with grid sizes used in urban facility accessibility literature

### 5.4 Spatial Weights Matrix

A **binary distance-band weights matrix** W is constructed using `libpysal.weights.DistanceBand` with:

- **Distance threshold:** 1,500 m (three cell widths)
- **Weight type:** binary (w_ij = 1 if within threshold, 0 otherwise)
- **Transform:** row-standardised (`w.transform = "r"`)

Under row-standardisation, each weight w_ij is divided by the row sum, so all weights for location i sum to 1. This makes the Gi* statistic a weighted average of neighbouring values, interpretable on a common scale regardless of the number of neighbours.

A threshold of 1,500 m means each cell's neighbourhood includes all cells whose centroids lie within 1.5 km — approximately 27 neighbours on average, which is sufficient for stable variance estimation.

### 5.5 Getis-Ord Gi* Statistic

The **Getis-Ord Gi\*** (G-star) local spatial statistic (Getis & Ord, 1992; Ord & Getis, 1995) tests whether the sum of values in a local neighbourhood is significantly larger or smaller than expected under spatial randomness.

For each grid cell i, the statistic is:

```
         Σⱼ wᵢⱼ xⱼ  −  x̄ Σⱼ wᵢⱼ
Gi* = ────────────────────────────────────────────────────
       S × √[ (n Σⱼ wᵢⱼ²  −  (Σⱼ wᵢⱼ)²) / (n − 1) ]
```

Where:
- **xⱼ** = facility count at cell j
- **x̄** = mean facility count across all n cells
- **S** = standard deviation of facility counts
- **wᵢⱼ** = spatial weight between cells i and j (row-standardised)
- **n** = total number of cells

The Gi* statistic differs from the standard Gi statistic in that it **includes the focal cell i in its own neighbourhood** (hence the asterisk). This is the standard formulation used in ArcGIS Spatial Statistics and esda.

**Implementation:**

```python
from esda.getisord import G_Local
gi = G_Local(y, w, transform="r", star=True, permutations=999)
```

- `y` — array of facility counts per cell
- `star=True` — uses the Gi* formulation (self-included)
- `permutations=999` — generates pseudo p-values by randomly shuffling the attribute values 999 times and comparing observed Gi* to the simulated distribution

**Output attributes stored per cell:**

| Field | Description |
|---|---|
| `Gi_z` | Standardised z-score |
| `Gi_p` | Pseudo p-value (999 permutations) |
| `Gi_EV` | Expected value of Gi* under null |
| `Gi_VR` | Variance of Gi* under null |

A **positive z-score** indicates the local sum is larger than expected (candidate hot spot).
A **negative z-score** indicates the local sum is smaller than expected (candidate cold spot).

### 5.6 Significance Classification

Each cell is classified based on both the **direction of the z-score** and the **pseudo p-value**, following the standard ArcGIS / ESDA convention:

| Class | Condition | Interpretation |
|---|---|---|
| Hot Spot 99% | z > 0 and p < 0.01 | Highly significant cluster of high values |
| Hot Spot 95% | z > 0 and p < 0.05 | Significant cluster of high values |
| Hot Spot 90% | z > 0 and p < 0.10 | Marginally significant cluster of high values |
| Not Significant | p ≥ 0.10 | No statistically significant spatial pattern |
| Cold Spot 90% | z < 0 and p < 0.10 | Marginally significant cluster of low values |
| Cold Spot 95% | z < 0 and p < 0.05 | Significant cluster of low values |
| Cold Spot 99% | z < 0 and p < 0.01 | Highly significant cluster of low values |

Classification is implemented as:

```python
def classify(z, p):
    if p < 0.01:
        return "Hot Spot 99%" if z > 0 else "Cold Spot 99%"
    elif p < 0.05:
        return "Hot Spot 95%" if z > 0 else "Cold Spot 95%"
    elif p < 0.10:
        return "Hot Spot 90%" if z > 0 else "Cold Spot 90%"
    else:
        return "Not Significant"
```

---

## 6. Software & Dependencies

### Python Environment

| Library | Version used | Purpose |
|---|---|---|
| `geopandas` | — | Spatial dataframes, CRS reprojection, spatial join, overlay |
| `libpysal` | — | Spatial weights matrix (`DistanceBand`) |
| `esda` | 2.8.1 | Getis-Ord Gi* computation (`G_Local`) |
| `numpy` | 2.3.1 | Grid construction, array operations |
| `scipy` | 1.16.0 | Skewness computation for histogram annotation |
| `matplotlib` | 3.10.3 | Static 5-panel map generation |
| `shapely` | — | Geometry construction (`box`, `Point`) |
| `pandas` | — | Tabular data manipulation |
| `json` | stdlib | GeoJSON loading and serialisation |

### Web Map

| Library | Version | Purpose |
|---|---|---|
| Leaflet.js | 1.9.4 | Interactive map rendering |
| CartoDB Basemaps | — | Dark tile basemap (default) |
| OpenStreetMap | — | Street basemap option |
| Esri World Imagery | — | Satellite basemap option |

Leaflet is loaded from CDN (`unpkg.com`). An internet connection is required only for the basemap tiles — the GeoJSON data and all application logic are **embedded directly** in the HTML file.

---

## 7. Installation

### Prerequisites

- Python 3.10 or later
- `pip` package manager

### Install required packages

```bash
pip install geopandas libpysal esda matplotlib scipy shapely
```

If `esda` is not found directly, install via:

```bash
pip install esda
```

### Verify installation

```bash
python -c "import geopandas, libpysal, esda, matplotlib, scipy; print('All OK')"
```

---

## 8. Running the Analysis

### Step 1 — Run the spatial analysis

```bash
python -X utf8 hotspot_analysis.py
```

The `-X utf8` flag is required on Windows to handle Unicode characters in print output. This script:

1. Loads and clips the raw GeoJSON to Mandalay District
2. Reprojects to UTM Zone 47N
3. Builds the 500 m fishnet grid
4. Counts facilities per cell via spatial join
5. Constructs the distance-band spatial weights matrix
6. Computes Getis-Ord Gi* with 999 permutations
7. Classifies each cell by significance level
8. Saves the static 5-panel PNG map
9. Exports `mandalay_hotspot_results.geojson`

**Expected console output:**

```
=================================================================
  SPATIAL HOT SPOT ANALYSIS – MANDALAY DISTRICT
  Method: Getis-Ord Gi*  |  Dataset: HOTOSM Myanmar
=================================================================

[1] Raw dataset loaded: 4,532 features across Myanmar
[2] Mandalay District clip: 180 facilities retained
    Bounding box: lon [95.85, 96.45]  lat [21.7, 22.2]

[3] Facility types in Mandalay District:
    school                     167
    university                   9
    kindergarten                 3
    college                      1

[4] Grid created: 8,690 cells  (500 m × 500 m)
    Cells with ≥ 1 facility: 130  (1.5 %)
    Max facilities per cell : 6
    Mean per occupied cell  : 1.37

[5] Spatial weights matrix built
    Distance threshold : 1,500 m
    Mean neighbours    : 27.2

[6] Getis-Ord Gi* Classification Summary
    Class                     Cells  % of total
    -------------------------------------------
    Hot Spot 99%                214        2.5%
    Hot Spot 95%                 97        1.1%
    Hot Spot 90%                121        1.4%
    Not Significant             955       11.0%
    Cold Spot 99%             7,303       84.0%

    Facilities in 99% Hot Spots: 123
    Facilities in 95% Hot Spots:  13
    Max Gi* z-score            : 8.079
    Min Gi* z-score            : -0.106

[7] Map saved → mandalay_hotspot_analysis.png
[8] Results GeoJSON → mandalay_hotspot_results.geojson
```

**Runtime:** approximately 60–120 seconds (dominated by the 999-permutation inference step).

### Step 2 — Build the web map

```bash
python -X utf8 build_webmap.py
```

This script:

1. Reads `mandalay_hotspot_results.geojson`
2. Minifies coordinates to 6 decimal places and statistics to 4 decimal places
3. Computes header statistics (total cells, facilities, hot/cold counts, max Z)
4. Generates the HTML template with all Leaflet code
5. Injects the minified GeoJSON and computed statistics as inline JavaScript
6. Writes `mandalay_hotspot_webmap.html`

**Expected output:**

```
HTML size : 2159 KB
Saved     : mandalay_hotspot_webmap.html
```

---

## 9. Results & Findings

### Gi* Classification Summary

| Class | Cells | Share | Facilities |
|---|---|---|---|
| Hot Spot 99% | 214 | 2.5% | 123 |
| Hot Spot 95% | 97 | 1.1% | 13 |
| Hot Spot 90% | 121 | 1.4% | — |
| Not Significant | 955 | 11.0% | — |
| Cold Spot 99% | 7,303 | 84.0% | — |
| **Total** | **8,690** | **100%** | **178** |

### Z-Score Distribution

| Statistic | Value |
|---|---|
| Maximum Gi* z-score | +8.079 |
| Minimum Gi* z-score | −0.106 |
| Mean z-score | (dominated by cold/NS cells near −0.1) |

### Key Findings

**1. One dominant urban core hot spot**

A single, spatially contiguous hot spot cluster is detected in the central-northern portion of the study area, corresponding to the dense urban grid of **Mandalay city proper** — specifically the central townships of Chanayethazan, Aungmyethazan, Mahaaungmye, and Chanmyathazi. The peak z-score of **+8.08** (p = 0.001) is nearly four times the 99% confidence threshold of 2.576, confirming an extremely strong spatial concentration of educational facilities in this area.

**2. 75% of facilities within hot-spot core**

The 99% + 95% hot spot cells collectively contain **136 of 180 facilities (75.6%)** despite covering only 3.6% of grid cells. This is the defining characteristic of the urban concentration pattern.

**3. No significant cold-spot clusters**

While 84% of cells are classified as Cold Spot 99%, this reflects the large number of **empty rural and peri-urban cells** rather than a concentrated zone of suppressed facility density. The near-zero negative z-score (minimum: −0.106) confirms there is no area where facility absence is significantly clustered — absence is uniformly spread across the rural periphery.

**4. Urban–rural educational access divide**

The pattern is consistent with a strongly centralised provision model: educational institutions are concentrated in the urban core, while outlying townships (Tada-U, Patheingyi in particular) have sparse provision relative to their land area.

### Interpretation Caveats

- Results reflect the **OSM-derived dataset coverage**, which may be incomplete in less-mapped areas. Absence of facilities in rural cells may partly reflect unmapped rather than absent institutions.
- The analysis measures **facility count density**, not enrolment, quality, or accessibility by road.
- The bounding box study area does not coincide exactly with the administrative boundary of Mandalay District.

---

## 10. Output Files

### `mandalay_hotspot_results.geojson`

GeoJSON FeatureCollection of 8,690 Polygon features. Each feature is one 500 m × 500 m grid cell with the following properties:

| Property | Type | Description |
|---|---|---|
| `count` | Integer | Number of educational facilities in the cell |
| `Gi_z` | Float | Getis-Ord Gi* z-score |
| `Gi_p` | Float | Pseudo p-value (999 permutations) |
| `class` | String | Significance class (see §5.6) |

CRS: WGS 84 (EPSG:4326). Compatible with QGIS, ArcGIS, Mapbox, and any GeoJSON-aware GIS tool.

**File size:** ~3.4 MB (unminified) / ~2.1 MB (minified, embedded in HTML)

### `mandalay_hotspot_analysis.png`

Static 5-panel analytical map at 180 dpi (approx. 3,600 × 2,340 px). Panels:

| Panel | Content |
|---|---|
| A (left, full height) | Gi* significance classification map with facility point overlay |
| B (top centre) | Continuous Gi* z-score choropleth (RdBu_r diverging scale) |
| C (top right) | Raw facility count per cell (YlOrRd scale, 99th-percentile cap) |
| D (bottom centre) | Distribution histogram of all Gi* z-scores with significance thresholds |
| E (bottom right) | Horizontal bar chart of cell counts by significance class |

### `mandalay_hotspot_webmap.html`

Fully self-contained interactive web map (~2.2 MB). Requires no web server — open directly in any modern browser. Requires internet access for basemap tiles only.

---

## 11. Web Map

### Opening the Map

Double-click `mandalay_hotspot_webmap.html` in Windows Explorer, or open it from any browser via `File > Open`.

### Map Controls

| Control | Location | Function |
|---|---|---|
| Zoom buttons | Top-right | Zoom in / out |
| Layer switcher | Top-right (layers icon) | Toggle between Dark, Streets, Satellite basemaps |
| Legend | Bottom-left | Shows significance classes with cell counts; click any row to toggle that layer on/off |
| Info panel | Bottom-right | Displays analysis parameters and key statistics |
| Scale bar | Bottom-right (below info) | Metric scale |

### Interactions

| Action | Effect |
|---|---|
| Hover over a cell | Tooltip showing significance class, Gi* z-score, facility count |
| Click a cell | Popup with full statistics: z-score (colour-coded), p-value with significance stars, facility count, proportional intensity bar |
| Click legend row | Toggles that significance class on/off (row dims when off) |
| Scroll / pinch | Zoom |
| Drag | Pan |

### Significance Stars in Popups

| Symbol | Meaning |
|---|---|
| `*** p < 0.01` | Highly significant (red) |
| `** p < 0.05` | Significant (orange) |
| `* p < 0.10` | Marginally significant (yellow) |
| `ns` | Not significant (grey) |

### Basemaps

| Option | Tile Provider | Best for |
|---|---|---|
| Dark (CartoDB) | CartoDB Dark Matter | Default; best contrast for coloured cells |
| Streets (OSM) | OpenStreetMap | Identifying roads and place names |
| Satellite (Esri) | Esri World Imagery | Matching clusters to physical urban fabric |

---

## 12. Limitations & Caveats

### Data Completeness
HOTOSM data is crowd-sourced via OpenStreetMap. Coverage in Mandalay city is relatively dense, but rural and peri-urban areas may have **systematic undercount** of facilities. Cold spots may partly reflect unmapped rather than absent schools.

### Modifiable Areal Unit Problem (MAUP)
The results depend on the chosen grid cell size (500 m) and distance threshold (1,500 m). Different parameterisations would produce different z-scores and cluster boundaries. The chosen values are grounded in the urban structure of Mandalay (~1 km block grid) but should be treated as one reasonable configuration, not a unique truth.

### Bounding Box Study Area
Mandalay District was approximated by a rectangular bounding box rather than the true administrative polygon. A small number of facilities from adjacent districts may have been included, and some district-edge cells may extend beyond the true boundary.

### Pseudo P-Values
Inference uses **conditional permutation** (999 randomisations) rather than analytical normality. While this is more robust for skewed, zero-heavy distributions, the minimum achievable p-value is 1/(999+1) = 0.001. All cells at this minimum p-value are indistinguishable in statistical strength.

### Point Count as Proxy
The analysis treats each facility point equally (count = 1). It does not account for facility size, enrolment, teaching staff, or service catchment area. A weighted analysis using enrolment data (when available) would produce more nuanced results.

### Zero Inflation
Only 1.5% of cells contain any facilities. The majority-zero distribution makes the cold spot pattern (84% of cells at 99% confidence) a mathematical artefact of the data structure rather than evidence of a meaningful spatial phenomenon at the Cold Spot end.

---

## 13. Colour Scheme Reference

The colour ramp follows the standard ArcGIS / ESDA hot spot convention (Ord & Getis, 1995):

| Class | Hex | RGB |
|---|---|---|
| Hot Spot 99% | `#d7191c` | 215, 25, 28 |
| Hot Spot 95% | `#f87c40` | 248, 124, 64 |
| Hot Spot 90% | `#fed789` | 254, 215, 137 |
| Not Significant | `#eeeeee` / `#2e2e4e` (web) | — |
| Cold Spot 90% | `#abd9e9` | 171, 217, 233 |
| Cold Spot 95% | `#4db3d7` | 77, 179, 215 |
| Cold Spot 99% | `#2c7bb6` | 44, 123, 182 |

The diverging red–blue palette is perceptually balanced and accessible for the most common forms of colour vision deficiency. The `Not Significant` colour is rendered as light grey in the static map and as near-transparent dark navy in the web map to minimise visual noise.

---

## 14. References

Anselin, L. (1995). Local indicators of spatial association — LISA. *Geographical Analysis*, 27(2), 93–115.

Getis, A., & Ord, J. K. (1992). The analysis of spatial association by use of distance statistics. *Geographical Analysis*, 24(3), 189–206.

Humanitarian OpenStreetMap Team (HOTOSM). (2024). *Myanmar Education Facilities*. Retrieved from https://data.humdata.org/

Ord, J. K., & Getis, A. (1995). Local spatial autocorrelation statistics: Distributional issues and an application. *Geographical Analysis*, 27(4), 286–306.

PySAL Development Team. (2024). *esda: Exploratory Spatial Data Analysis* (v2.8.1). https://pysal.org/esda/

PySAL Development Team. (2024). *libpysal: Core PySAL Library* https://pysal.org/libpysal/

Agafonkin, V., et al. (2024). *Leaflet: an open-source JavaScript library for interactive maps* (v1.9.4). https://leafletjs.com/

---

*Documentation prepared for the Mandalay District Educational Facility Hot Spot Analysis project. All analysis performed in Python 3.13 on Windows 11.*
