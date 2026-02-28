"""
Spatial Hot Spot Analysis (Getis-Ord Gi*) for Educational Facilities in Mandalay District
Dataset: HOTOSM Myanmar Education Facilities Points
"""

import json
import numpy as np
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, box
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.colorbar import ColorbarBase
import matplotlib.gridspec as gridspec
from scipy import stats
from libpysal.weights import DistanceBand
from esda.getisord import G_Local
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# 1. LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 65)
print("  SPATIAL HOT SPOT ANALYSIS – MANDALAY DISTRICT")
print("  Method: Getis-Ord Gi*  |  Dataset: HOTOSM Myanmar")
print("=" * 65)

with open(
    r"C:\Users\Tin Ko Oo\Desktop\demo\hotosm_mmr_education_facilities_points_geojson.geojson",
    encoding="utf-8",
) as f:
    raw = json.load(f)

gdf_all = gpd.GeoDataFrame.from_features(raw["features"], crs="EPSG:4326")
print(f"\n[1] Raw dataset loaded: {len(gdf_all):,} features across Myanmar")

# ─────────────────────────────────────────────────────────────────────────────
# 2. CLIP TO MANDALAY DISTRICT  (approximate bounding box)
#    Mandalay District townships: Mandalay, Aungmyethazan, Chanayethazan,
#    Mahaaungmye, Chanmyathazi, Pyigyidagun, Patheingyi, Amarapura, Tada-U
# ─────────────────────────────────────────────────────────────────────────────
MANDALAY_BBOX = (95.85, 21.70, 96.45, 22.20)   # (min_lon, min_lat, max_lon, max_lat)
mandalay_box  = box(*MANDALAY_BBOX)

gdf = gdf_all[gdf_all.geometry.within(mandalay_box)].copy().reset_index(drop=True)
print(f"[2] Mandalay District clip: {len(gdf):,} facilities retained")
print(f"    Bounding box: lon [{MANDALAY_BBOX[0]}, {MANDALAY_BBOX[2]}]  "
      f"lat [{MANDALAY_BBOX[1]}, {MANDALAY_BBOX[3]}]")

if len(gdf) < 10:
    raise RuntimeError("Too few points in Mandalay District bbox – check coordinates.")

# Amenity breakdown
print("\n[3] Facility types in Mandalay District:")
if "amenity" in gdf.columns:
    for val, cnt in gdf["amenity"].value_counts().items():
        print(f"    {val:<25} {cnt:>4}")

# ─────────────────────────────────────────────────────────────────────────────
# 3. PROJECT TO METRIC CRS  (UTM zone 47N – covers central Myanmar)
# ─────────────────────────────────────────────────────────────────────────────
gdf_utm = gdf.to_crs("EPSG:32647")   # WGS 84 / UTM zone 47N

# ─────────────────────────────────────────────────────────────────────────────
# 4. BUILD REGULAR FISHNET GRID  (cell size ≈ 500 m × 500 m)
# ─────────────────────────────────────────────────────────────────────────────
CELL_M = 500          # grid resolution in metres

bounds = gdf_utm.total_bounds   # (minx, miny, maxx, maxy)
xs = np.arange(bounds[0], bounds[2] + CELL_M, CELL_M)
ys = np.arange(bounds[1], bounds[3] + CELL_M, CELL_M)

rows, cols = [], []
polygons   = []
cx_list, cy_list = [], []

for i, y0 in enumerate(ys[:-1]):
    for j, x0 in enumerate(xs[:-1]):
        cell = box(x0, y0, x0 + CELL_M, y0 + CELL_M)
        polygons.append(cell)
        rows.append(i)
        cols.append(j)
        cx_list.append(x0 + CELL_M / 2)
        cy_list.append(y0 + CELL_M / 2)

grid = gpd.GeoDataFrame(
    {"row": rows, "col": cols, "cx": cx_list, "cy": cy_list},
    geometry=polygons,
    crs="EPSG:32647",
)

# Spatial join: count facilities per cell
joined = gpd.sjoin(gdf_utm, grid, how="left", predicate="within")
counts = joined.groupby("index_right").size().rename("count")
grid   = grid.join(counts, how="left")
grid["count"] = grid["count"].fillna(0).astype(int)

# Drop cells completely outside the area of interest
study_area_utm = gpd.GeoDataFrame(
    geometry=[mandalay_box], crs="EPSG:4326"
).to_crs("EPSG:32647")

grid = gpd.overlay(grid, study_area_utm, how="intersection")
grid = grid.reset_index(drop=True)

n_cells   = len(grid)
n_nonzero = (grid["count"] > 0).sum()
print(f"\n[4] Grid created: {n_cells:,} cells  ({CELL_M} m × {CELL_M} m)")
print(f"    Cells with ≥ 1 facility: {n_nonzero:,}  "
      f"({100*n_nonzero/n_cells:.1f} %)")
print(f"    Max facilities per cell : {grid['count'].max()}")
print(f"    Mean per occupied cell  : {grid.loc[grid['count']>0,'count'].mean():.2f}")

# ─────────────────────────────────────────────────────────────────────────────
# 5. SPATIAL WEIGHTS  (distance-band, threshold = 1 500 m ≈ 3 cell widths)
# ─────────────────────────────────────────────────────────────────────────────
THRESH_M = 1500   # neighbourhood radius

coords = np.column_stack([grid.geometry.centroid.x, grid.geometry.centroid.y])
w = DistanceBand(coords, threshold=THRESH_M, binary=True, silence_warnings=True)
w.transform = "r"   # row-standardise

print(f"\n[5] Spatial weights matrix built")
print(f"    Distance threshold : {THRESH_M:,} m")
print(f"    Mean neighbours    : {w.mean_neighbors:.1f}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. GETIS-ORD Gi*  (local G statistic with row-standardised weights)
# ─────────────────────────────────────────────────────────────────────────────
y = grid["count"].values.astype(float)
gi = G_Local(y, w, transform="r", star=True, permutations=999)

grid["Gi_z"]  = gi.Zs        # z-score
grid["Gi_p"]  = gi.p_sim     # simulated p-value
grid["Gi_EV"] = gi.EGs       # expected value
grid["Gi_VR"] = gi.VGs       # variance

# ─────────────────────────────────────────────────────────────────────────────
# 7. SIGNIFICANCE CLASSIFICATION
#    Confidence levels:  99 % → |z|>2.576 p<0.01
#                        95 % → |z|>1.960 p<0.05
#                        90 % → |z|>1.645 p<0.10
# ─────────────────────────────────────────────────────────────────────────────
def classify(z, p):
    if p < 0.01:
        return "Hot Spot 99%" if z > 0 else "Cold Spot 99%"
    elif p < 0.05:
        return "Hot Spot 95%" if z > 0 else "Cold Spot 95%"
    elif p < 0.10:
        return "Hot Spot 90%" if z > 0 else "Cold Spot 90%"
    else:
        return "Not Significant"

grid["class"] = [classify(z, p) for z, p in zip(grid["Gi_z"], grid["Gi_p"])]

class_order = [
    "Hot Spot 99%", "Hot Spot 95%", "Hot Spot 90%",
    "Not Significant",
    "Cold Spot 90%", "Cold Spot 95%", "Cold Spot 99%",
]
class_colors = {
    "Hot Spot 99%"   : "#d7191c",
    "Hot Spot 95%"   : "#f87c40",
    "Hot Spot 90%"   : "#fed789",
    "Not Significant": "#eeeeee",
    "Cold Spot 90%"  : "#abd9e9",
    "Cold Spot 95%"  : "#4db3d7",
    "Cold Spot 99%"  : "#2c7bb6",
}

# Summary table
print("\n[6] Getis-Ord Gi* Classification Summary")
print(f"    {'Class':<22}  {'Cells':>7}  {'% of total':>10}")
print("    " + "-" * 43)
total = len(grid)
for cls in class_order:
    cnt = (grid["class"] == cls).sum()
    if cnt > 0:
        pct = 100 * cnt / total
        print(f"    {cls:<22}  {cnt:>7,}  {pct:>9.1f}%")

hot99  = grid[grid["class"] == "Hot Spot 99%"]
hot95  = grid[grid["class"] == "Hot Spot 95%"]
print(f"\n    Facilities in 99% Hot Spots: {grid.loc[grid['class']=='Hot Spot 99%','count'].sum()}")
print(f"    Facilities in 95% Hot Spots: {grid.loc[grid['class']=='Hot Spot 95%','count'].sum()}")
print(f"    Max Gi* z-score            : {grid['Gi_z'].max():.3f}")
print(f"    Min Gi* z-score            : {grid['Gi_z'].min():.3f}")

# ─────────────────────────────────────────────────────────────────────────────
# 8. VISUALISATION
# ─────────────────────────────────────────────────────────────────────────────
grid_4326    = grid.to_crs("EPSG:4326")
gdf_pts_4326 = gdf.copy()

fig = plt.figure(figsize=(20, 13))
fig.patch.set_facecolor("#1a1a2e")

gs = gridspec.GridSpec(
    2, 3,
    figure=fig,
    left=0.03, right=0.97,
    top=0.91, bottom=0.04,
    wspace=0.05, hspace=0.30,
)

# ── Axes ─────────────────────────────────────────────────────────────────────
ax_hot  = fig.add_subplot(gs[:, 0])   # main hot spot map (left, tall)
ax_zi   = fig.add_subplot(gs[0, 1])   # Gi* z-score map (top middle)
ax_cnt  = fig.add_subplot(gs[0, 2])   # raw count map  (top right)
ax_hist = fig.add_subplot(gs[1, 1])   # histogram of z-scores
ax_stats= fig.add_subplot(gs[1, 2])   # bar chart by class

BG   = "#1a1a2e"
AXES = "#16213e"

for ax in [ax_hot, ax_zi, ax_cnt, ax_hist, ax_stats]:
    ax.set_facecolor(AXES)
    for spine in ax.spines.values():
        spine.set_edgecolor("#444466")

# ── Panel A – Getis-Ord Gi* Classification ───────────────────────────────────
present_classes = [c for c in class_order if (grid_4326["class"] == c).any()]
for cls in present_classes:
    grid_4326[grid_4326["class"] == cls].plot(
        ax=ax_hot, color=class_colors[cls],
        linewidth=0, alpha=0.92
    )
# Overlay facility points
gdf_pts_4326.plot(ax=ax_hot, color="black", markersize=3, alpha=0.4, zorder=5)

ax_hot.set_title(
    "Getis-Ord Gi* Hot Spot Analysis\nMandalay District – Educational Facilities",
    color="white", fontsize=11, fontweight="bold", pad=8
)
ax_hot.set_xlabel("Longitude", color="#aaaacc", fontsize=8)
ax_hot.set_ylabel("Latitude",  color="#aaaacc", fontsize=8)
ax_hot.tick_params(colors="#aaaacc", labelsize=7)

patches = [
    mpatches.Patch(color=class_colors[c], label=c)
    for c in class_order if (grid_4326["class"] == c).any()
]
patches.append(mpatches.Patch(color="black", label="Facilities (pts)", alpha=0.5))
ax_hot.legend(
    handles=patches, loc="lower left", fontsize=7,
    facecolor="#0f3460", edgecolor="#444466", labelcolor="white",
    title="Significance", title_fontsize=8,
)

# ── Panel B – Gi* Z-score Continuous Map ─────────────────────────────────────
vmax = max(abs(grid_4326["Gi_z"].max()), abs(grid_4326["Gi_z"].min()))
grid_4326.plot(
    column="Gi_z", ax=ax_zi, cmap="RdBu_r",
    vmin=-vmax, vmax=vmax, linewidth=0, alpha=0.9
)
sm = plt.cm.ScalarMappable(
    cmap="RdBu_r", norm=plt.Normalize(vmin=-vmax, vmax=vmax)
)
sm.set_array([])
cb = fig.colorbar(sm, ax=ax_zi, shrink=0.7, pad=0.02)
cb.ax.yaxis.set_tick_params(color="white")
plt.setp(cb.ax.yaxis.get_ticklabels(), color="white", fontsize=7)
cb.set_label("Gi* Z-score", color="white", fontsize=8)

ax_zi.set_title("Gi* Z-Score (continuous)", color="white", fontsize=9, fontweight="bold")
ax_zi.tick_params(colors="#aaaacc", labelsize=6)
ax_zi.axhline(y=grid_4326.total_bounds[1], color="none")

# ── Panel C – Raw Count Heatmap ───────────────────────────────────────────────
grid_4326.plot(
    column="count", ax=ax_cnt, cmap="YlOrRd",
    vmin=0, vmax=grid_4326["count"].quantile(0.99),
    linewidth=0, alpha=0.9, missing_kwds={"color": "#1a1a2e"}
)
sm2 = plt.cm.ScalarMappable(
    cmap="YlOrRd",
    norm=plt.Normalize(vmin=0, vmax=grid_4326["count"].quantile(0.99))
)
sm2.set_array([])
cb2 = fig.colorbar(sm2, ax=ax_cnt, shrink=0.7, pad=0.02)
cb2.ax.yaxis.set_tick_params(color="white")
plt.setp(cb2.ax.yaxis.get_ticklabels(), color="white", fontsize=7)
cb2.set_label("Facility count", color="white", fontsize=8)

ax_cnt.set_title(f"Raw Facility Count per {CELL_M}m Cell", color="white", fontsize=9, fontweight="bold")
ax_cnt.tick_params(colors="#aaaacc", labelsize=6)

# ── Panel D – Z-score Histogram ───────────────────────────────────────────────
zs = grid_4326["Gi_z"].values
ax_hist.hist(zs, bins=50, color="#4db3d7", edgecolor="#1a1a2e", linewidth=0.3, alpha=0.85)
for thresh, col, lab in [
    ( 1.645, "#fed789", "+1.65 (90%)"),
    ( 1.960, "#f87c40", "+1.96 (95%)"),
    ( 2.576, "#d7191c", "+2.58 (99%)"),
    (-1.645, "#abd9e9", "−1.65 (90%)"),
    (-1.960, "#4db3d7", "−1.96 (95%)"),
    (-2.576, "#2c7bb6", "−2.58 (99%)"),
]:
    ax_hist.axvline(thresh, color=col, linewidth=1.2, linestyle="--", alpha=0.8)
ax_hist.set_title("Distribution of Gi* Z-Scores", color="white", fontsize=9, fontweight="bold")
ax_hist.set_xlabel("Z-score", color="#aaaacc", fontsize=8)
ax_hist.set_ylabel("Cell count", color="#aaaacc", fontsize=8)
ax_hist.tick_params(colors="#aaaacc", labelsize=7)
ax_hist.text(
    0.97, 0.95,
    f"Mean: {zs.mean():.3f}\nSD: {zs.std():.3f}\nSkew: {stats.skew(zs):.3f}",
    transform=ax_hist.transAxes, ha="right", va="top",
    color="white", fontsize=7,
    bbox=dict(boxstyle="round,pad=0.3", facecolor="#0f3460", edgecolor="#444466"),
)

# ── Panel E – Class Bar Chart ─────────────────────────────────────────────────
bar_data = {c: (grid["class"] == c).sum() for c in class_order}
bar_data = {k: v for k, v in bar_data.items() if v > 0}
bars = ax_stats.barh(
    list(bar_data.keys()),
    list(bar_data.values()),
    color=[class_colors[k] for k in bar_data],
    edgecolor="#1a1a2e", linewidth=0.5
)
ax_stats.set_title("Cell Count by Significance Class", color="white", fontsize=9, fontweight="bold")
ax_stats.set_xlabel("Number of cells", color="#aaaacc", fontsize=8)
ax_stats.tick_params(colors="#aaaacc", labelsize=7)
for bar, (cls, val) in zip(bars, bar_data.items()):
    ax_stats.text(
        bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
        f"{val:,}", va="center", ha="left", color="white", fontsize=7
    )
ax_stats.set_xlim(0, max(bar_data.values()) * 1.18)

# ── Super-title ───────────────────────────────────────────────────────────────
fig.suptitle(
    "Spatial Hot Spot Analysis: Educational Facility Clusters in Mandalay District\n"
    "Getis-Ord Gi* | 999 permutations | Distance band: 1,500 m | Grid: 500 m",
    color="white", fontsize=13, fontweight="bold", y=0.975
)

OUT_PATH = r"C:\Users\Tin Ko Oo\Desktop\demo\mandalay_hotspot_analysis.png"
plt.savefig(OUT_PATH, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"\n[7] Map saved → {OUT_PATH}")

# ─────────────────────────────────────────────────────────────────────────────
# 9. EXPORT RESULTS AS GEOJSON  (for GIS use)
# ─────────────────────────────────────────────────────────────────────────────
out_geojson = r"C:\Users\Tin Ko Oo\Desktop\demo\mandalay_hotspot_results.geojson"
export_cols = ["count", "Gi_z", "Gi_p", "class", "geometry"]
grid_4326[export_cols].to_file(out_geojson, driver="GeoJSON")
print(f"[8] Results GeoJSON → {out_geojson}")

# ─────────────────────────────────────────────────────────────────────────────
# 10. SUMMARY INTERPRETATION
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("  INTERPRETATION SUMMARY")
print("=" * 65)

hot99_count  = (grid["class"] == "Hot Spot 99%").sum()
hot95_count  = (grid["class"] == "Hot Spot 95%").sum()
cold99_count = (grid["class"] == "Cold Spot 99%").sum()
ns_count     = (grid["class"] == "Not Significant").sum()

if not hot99.empty:
    cx99 = hot99_count
    fac99 = grid.loc[grid["class"] == "Hot Spot 99%", "count"].sum()
    print(f"\n  CORE HOT SPOTS (99% confidence):")
    print(f"  → {hot99_count} grid cells, containing {fac99} facilities")
    z_top5 = grid.nlargest(5, "Gi_z")[["cx","cy","count","Gi_z","Gi_p"]]
    print(f"\n  Top-5 cells by Gi* Z-score:")
    for _, r in z_top5.iterrows():
        print(f"    Z={r.Gi_z:>6.3f}  p={r.Gi_p:.4f}  count={int(r['count']):>3}")

print(f"\n  Statistical overview:")
print(f"  Total cells analysed        : {len(grid):,}")
print(f"  Total facilities (district) : {int(grid['count'].sum())}")
sig_hot  = ((grid["Gi_p"] < 0.05) & (grid["Gi_z"] > 0)).sum()
sig_cold = ((grid["Gi_p"] < 0.05) & (grid["Gi_z"] < 0)).sum()
print(f"  Sig. hot  cells (p<0.05)    : {sig_hot}")
print(f"  Sig. cold cells (p<0.05)    : {sig_cold}")
print(f"  Not-significant cells       : {ns_count}")
print("=" * 65)
print("  Analysis complete.")
print("=" * 65)
