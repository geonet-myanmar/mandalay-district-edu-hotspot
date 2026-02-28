import json, os

# ── Load & minify GeoJSON ────────────────────────────────────────────
with open(r"C:\Users\Tin Ko Oo\Desktop\demo\mandalay_hotspot_results.geojson", encoding="utf-8") as f:
    data = json.load(f)

for ft in data["features"]:
    geom = ft["geometry"]
    if geom["type"] == "Polygon":
        geom["coordinates"] = [
            [[round(x, 6), round(y, 6)] for x, y in ring]
            for ring in geom["coordinates"]
        ]
    p = ft["properties"]
    p["Gi_z"] = round(p["Gi_z"], 4)
    p["Gi_p"] = round(p["Gi_p"], 4)

geojson_str = json.dumps(data, separators=(",", ":"))

# ── Summary stats ─────────────────────────────────────────────────────
classes = {}
total_fac = 0
max_z = -999; min_z = 999
for ft in data["features"]:
    p  = ft["properties"]
    c  = p["class"]
    classes[c] = classes.get(c, 0) + 1
    total_fac += p["count"]
    if p["Gi_z"] > max_z: max_z = p["Gi_z"]
    if p["Gi_z"] < min_z: min_z = p["Gi_z"]

total    = sum(classes.values())
sig_hot  = classes.get("Hot Spot 99%", 0) + classes.get("Hot Spot 95%", 0)
sig_cold = classes.get("Cold Spot 99%", 0) + classes.get("Cold Spot 95%", 0)
max_z_r  = round(max_z, 4)
min_z_r  = round(min_z, 3)

# ── HTML template ─────────────────────────────────────────────────────
html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Mandalay District – Hot Spot Analysis</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"><\/script>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',Arial,sans-serif;background:#0f1117;color:#e0e0f0;height:100vh;display:flex;flex-direction:column}

    /* HEADER */
    #hdr{background:linear-gradient(135deg,#1a1a2e,#16213e);border-bottom:1px solid #2a2a5a;
         padding:9px 16px;display:flex;align-items:center;gap:14px;flex-shrink:0;
         box-shadow:0 2px 14px rgba(0,0,0,.55);z-index:1000}
    .badge{background:#d7191c;color:#fff;font-size:9.5px;font-weight:700;padding:3px 7px;
           border-radius:3px;letter-spacing:.6px;text-transform:uppercase;white-space:nowrap}
    #hdr h1{font-size:14px;font-weight:700;color:#fff;letter-spacing:.2px}
    #hdr p{font-size:10.5px;color:#7777aa;margin-top:1px}
    .spacer{flex:1}
    .chip{background:#0f3460;border:1px solid #2244aa;border-radius:6px;padding:5px 11px;
          text-align:center;min-width:76px}
    .chip .v{font-size:15px;font-weight:700;color:#5bc0de}
    .chip .l{font-size:9px;color:#7777aa;text-transform:uppercase;letter-spacing:.5px}

    /* MAP */
    #map{flex:1;width:100%}

    /* LEGEND */
    .legend{background:rgba(12,14,26,.94);border:1px solid #2a2a5a;border-radius:8px;
            padding:11px 13px;min-width:180px;box-shadow:0 4px 20px rgba(0,0,0,.65);
            backdrop-filter:blur(6px)}
    .legend h4{font-size:10px;font-weight:700;color:#8888bb;text-transform:uppercase;
               letter-spacing:1px;margin-bottom:9px;border-bottom:1px solid #2a2a5a;
               padding-bottom:5px}
    .lrow{display:flex;align-items:center;gap:7px;margin-bottom:4px;cursor:pointer;
          padding:3px 4px;border-radius:4px;transition:background .15s}
    .lrow:hover{background:rgba(255,255,255,.06)}
    .lrow.off{opacity:.3}
    .swatch{width:16px;height:16px;border-radius:3px;flex-shrink:0;
            border:1px solid rgba(255,255,255,.12)}
    .llabel{font-size:11px;color:#ccccee;flex:1}
    .lcnt{font-size:10px;color:#555577}
    .ldiv{border:none;border-top:1px solid #2a2a5a;margin:6px 0}
    .lnote{font-size:9px;color:#555577;line-height:1.45;margin-top:6px}

    /* POPUP */
    .leaflet-popup-content-wrapper{background:rgba(12,14,26,.97);border:1px solid #2a2a5a;
      border-radius:8px;color:#e0e0f0;box-shadow:0 4px 22px rgba(0,0,0,.75)}
    .leaflet-popup-tip{background:rgba(12,14,26,.97)}
    .ptitle{font-size:12px;font-weight:700;margin-bottom:8px}
    .pgrid{display:grid;grid-template-columns:auto 1fr;gap:3px 10px;font-size:11px}
    .pgrid .k{color:#7777aa}
    .pgrid .v{color:#e0e0f0;font-weight:600}
    .pbadge{display:inline-block;padding:2px 7px;border-radius:3px;font-size:10px;
            font-weight:700;letter-spacing:.3px}
    .zbar-wrap{margin:7px 0 2px}
    .zbar-lbl{font-size:9px;color:#7777aa;margin-bottom:3px}
    .zbar-bg{background:#1a1a2e;border-radius:3px;height:6px;overflow:hidden}
    .zbar-fill{height:100%;border-radius:3px;transition:width .3s}

    /* INFO PANEL */
    .infopanel{background:rgba(12,14,26,.94);border:1px solid #2a2a5a;border-radius:8px;
               padding:10px 13px;min-width:170px;font-size:10.5px;color:#9999bb;
               box-shadow:0 4px 20px rgba(0,0,0,.6)}
    .infopanel h4{font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:1px;
                  color:#5555aa;margin-bottom:7px;border-bottom:1px solid #2a2a5a;
                  padding-bottom:4px}
    .irow{display:flex;justify-content:space-between;gap:10px;margin-bottom:3px}
    .irow .iv{color:#5bc0de;font-weight:700}

    /* TOOLTIP */
    .leaflet-tooltip{background:rgba(12,14,26,.93);border:1px solid #2a2a5a;color:#e0e0f0;
                     font-size:11px;border-radius:5px;padding:4px 8px;
                     box-shadow:0 2px 8px rgba(0,0,0,.5)}
  </style>
</head>
<body>

<div id="hdr">
  <span class="badge">Hot Spot</span>
  <div>
    <h1>Mandalay District &mdash; Educational Facility Cluster Analysis</h1>
    <p>Getis-Ord Gi* &nbsp;&bull;&nbsp; 999 permutations &nbsp;&bull;&nbsp; 500&thinsp;m grid &nbsp;&bull;&nbsp; 1&thinsp;500&thinsp;m distance band &nbsp;&bull;&nbsp; HOTOSM Myanmar</p>
  </div>
  <div class="spacer"></div>
  <div class="chip"><div class="v">TOTAL_CELLS</div><div class="l">Grid Cells</div></div>
  <div class="chip"><div class="v">TOTAL_FAC</div><div class="l">Facilities</div></div>
  <div class="chip"><div class="v" style="color:#d7191c">SIG_HOT</div><div class="l">Hot p&lt;.05</div></div>
  <div class="chip"><div class="v" style="color:#4db3d7">SIG_COLD</div><div class="l">Cold p&lt;.05</div></div>
  <div class="chip"><div class="v" style="color:#ffd700">MAX_Z</div><div class="l">Max Z-Score</div></div>
</div>

<div id="map"></div>

<script>
const HOTSPOT_DATA = GEOJSON_PLACEHOLDER;

const CLASS_STYLE = {
  "Hot Spot 99%":    {color:"#d7191c", badgeColor:"#d7191c"},
  "Hot Spot 95%":    {color:"#f87c40", badgeColor:"#f87c40"},
  "Hot Spot 90%":    {color:"#fed789", badgeColor:"#b89000"},
  "Not Significant": {color:"#2e2e4e", badgeColor:"#555577"},
  "Cold Spot 90%":   {color:"#abd9e9", badgeColor:"#abd9e9"},
  "Cold Spot 95%":   {color:"#4db3d7", badgeColor:"#4db3d7"},
  "Cold Spot 99%":   {color:"#2c7bb6", badgeColor:"#2c7bb6"},
};
const CLASS_ORDER = [
  "Hot Spot 99%","Hot Spot 95%","Hot Spot 90%",
  "Not Significant",
  "Cold Spot 90%","Cold Spot 95%","Cold Spot 99%"
];
const MAX_Z = MAX_Z_PLACEHOLDER;

// ── Map init ──────────────────────────────────────────────────────
const map = L.map("map",{center:[21.955,96.09],zoom:11,zoomControl:false});
L.control.zoom({position:"topright"}).addTo(map);

const basemaps = {
  "Dark (CartoDB)": L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    {attribution:"&copy; OpenStreetMap &copy; CartoDB",subdomains:"abcd",maxZoom:19}),
  "Streets (OSM)": L.tileLayer(
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    {attribution:"&copy; OpenStreetMap contributors",maxZoom:19}),
  "Satellite (Esri)": L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {attribution:"&copy; Esri",maxZoom:18}),
};
basemaps["Dark (CartoDB)"].addTo(map);

// ── Layer groups ──────────────────────────────────────────────────
const layerGroups = {};
const classCounts = {};
CLASS_ORDER.forEach(cls => { layerGroups[cls] = L.layerGroup(); classCounts[cls] = 0; });

function styleFn(feature) {
  const cls = feature.properties.class;
  const st  = CLASS_STYLE[cls] || {color:"#888"};
  const isNS = cls === "Not Significant";
  return {
    fillColor  : st.color,
    fillOpacity: isNS ? 0.15 : 0.75,
    color      : isNS ? "transparent" : "rgba(0,0,0,0.2)",
    weight     : 0.4,
  };
}

function popupHTML(p) {
  const st = CLASS_STYLE[p.class] || {badgeColor:"#888",color:"#888"};
  const absZ = Math.abs(p.Gi_z);
  const barW = Math.min(absZ / MAX_Z * 100, 100).toFixed(1);
  const sigTag = p.Gi_p < 0.01
    ? '<span style="color:#d7191c;font-size:9px"> *** p&lt;0.01</span>'
    : p.Gi_p < 0.05
    ? '<span style="color:#f87c40;font-size:9px"> ** p&lt;0.05</span>'
    : p.Gi_p < 0.10
    ? '<span style="color:#fed789;font-size:9px"> * p&lt;0.10</span>'
    : '<span style="color:#444466;font-size:9px"> ns</span>';
  const zColor = p.Gi_z > 0 ? "#f87c40" : "#4db3d7";
  const zStr   = (p.Gi_z > 0 ? "+" : "") + p.Gi_z.toFixed(4);
  return `<div style="min-width:210px">
    <div class="ptitle">
      <span class="pbadge" style="background:${st.badgeColor}22;color:${st.badgeColor};border:1px solid ${st.badgeColor}55">
        ${p.class}
      </span>
    </div>
    <div class="pgrid">
      <span class="k">Gi* Z-score</span><span class="v" style="color:${zColor}">${zStr}</span>
      <span class="k">p-value</span><span class="v">${p.Gi_p.toFixed(4)}${sigTag}</span>
      <span class="k">Facilities</span><span class="v">${p.count}</span>
    </div>
    ${p.class !== "Not Significant" ? `
    <div class="zbar-wrap">
      <div class="zbar-lbl">Gi* intensity (${barW}% of max)</div>
      <div class="zbar-bg"><div class="zbar-fill" style="width:${barW}%;background:${st.badgeColor}"></div></div>
    </div>` : ""}
  </div>`;
}

HOTSPOT_DATA.features.forEach(ft => {
  const cls = ft.properties.class;
  if (!layerGroups[cls]) return;
  classCounts[cls]++;
  const lyr = L.geoJSON(ft, {
    style: styleFn,
    onEachFeature(feature, layer) {
      const p = feature.properties;
      const zStr = (p.Gi_z > 0 ? "+" : "") + p.Gi_z.toFixed(3);
      layer.bindTooltip(
        `<b>${p.class}</b> &nbsp; Z = ${zStr} &nbsp;|&nbsp; Facilities: ${p.count}`,
        {sticky:true, opacity:0.95}
      );
      layer.bindPopup(popupHTML(p), {maxWidth:270});
      layer.on("mouseover", function() {
        if (p.class !== "Not Significant") {
          this.setStyle({fillOpacity:0.95, weight:1.8, color:"rgba(255,255,255,0.7)"});
          this.bringToFront();
        }
      });
      layer.on("mouseout", function() { this.setStyle(styleFn(feature)); });
    },
  });
  layerGroups[cls].addLayer(lyr);
});

// Add layers to map (NS first = bottom)
[...CLASS_ORDER].reverse().forEach(cls => layerGroups[cls].addTo(map));

// ── Legend ────────────────────────────────────────────────────────
const legendCtrl = L.control({position:"bottomleft"});
legendCtrl.onAdd = function() {
  const div = L.DomUtil.create("div","legend");
  L.DomEvent.disableClickPropagation(div);
  const active = {};
  CLASS_ORDER.forEach(c => active[c] = true);

  function render() {
    div.innerHTML = "<h4>Gi* Significance</h4>";
    CLASS_ORDER.forEach(cls => {
      const cnt = classCounts[cls] || 0;
      if (!cnt) return;
      const st  = CLASS_STYLE[cls];
      const row = document.createElement("div");
      row.className = "lrow" + (active[cls] ? "" : " off");
      row.title = `Click to toggle ${cls}`;
      row.innerHTML = `<div class="swatch" style="background:${st.color};${cls==="Not Significant"?"opacity:.35;":""}"></div>
        <span class="llabel">${cls}</span>
        <span class="lcnt">${cnt.toLocaleString()}</span>`;
      row.onclick = () => {
        active[cls] = !active[cls];
        active[cls] ? map.addLayer(layerGroups[cls]) : map.removeLayer(layerGroups[cls]);
        render();
      };
      div.appendChild(row);
    });
    const hr = document.createElement("hr");
    hr.className = "ldiv";
    div.appendChild(hr);
    const note = document.createElement("div");
    note.className = "lnote";
    note.innerHTML = "Click rows to toggle layers.<br>Click cells for statistics.";
    div.appendChild(note);
  }
  render();
  return div;
};
legendCtrl.addTo(map);

// ── Info panel ────────────────────────────────────────────────────
const infoCtrl = L.control({position:"bottomright"});
infoCtrl.onAdd = function() {
  const div = L.DomUtil.create("div","infopanel");
  L.DomEvent.disableClickPropagation(div);
  div.innerHTML = `
    <h4>Analysis Parameters</h4>
    <div class="irow"><span>Method</span>       <span class="iv">Getis-Ord Gi*</span></div>
    <div class="irow"><span>Grid size</span>    <span class="iv">500 m &times; 500 m</span></div>
    <div class="irow"><span>Distance</span>     <span class="iv">1,500 m band</span></div>
    <div class="irow"><span>Weights</span>      <span class="iv">Row-standardised</span></div>
    <div class="irow"><span>Permutations</span> <span class="iv">999</span></div>
    <div class="irow"><span>Max Z-score</span>  <span class="iv" style="color:#d7191c">+MAX_Z_DISP</span></div>
    <div class="irow"><span>Min Z-score</span>  <span class="iv" style="color:#4db3d7">MIN_Z_DISP</span></div>
    <div class="irow"><span>Facilities</span>   <span class="iv">TOTAL_FAC_DISP</span></div>
    <div class="irow"><span>CRS</span>          <span class="iv">WGS 84 (EPSG:4326)</span></div>
  `;
  return div;
};
infoCtrl.addTo(map);

// ── Basemap switcher & scale ──────────────────────────────────────
L.control.layers(basemaps, {}, {position:"topright", collapsed:true}).addTo(map);
L.control.scale({imperial:false, position:"bottomright"}).addTo(map);

// ── Fit to data ───────────────────────────────────────────────────
map.fitBounds(L.geoJSON(HOTSPOT_DATA).getBounds(), {padding:[20,20]});
<\/script>
</body>
</html>"""

# ── Inject dynamic values ──────────────────────────────────────────
html = html.replace("GEOJSON_PLACEHOLDER", geojson_str)
html = html.replace("MAX_Z_PLACEHOLDER", str(max_z_r))
html = html.replace("TOTAL_CELLS", f"{total:,}")
html = html.replace("TOTAL_FAC", str(int(total_fac)))
html = html.replace("SIG_HOT",  str(sig_hot))
html = html.replace("SIG_COLD", f"{sig_cold:,}")
html = html.replace("MAX_Z",    str(round(max_z, 2)))
html = html.replace("MAX_Z_DISP", str(round(max_z, 3)))
html = html.replace("MIN_Z_DISP", str(round(min_z, 3)))
html = html.replace("TOTAL_FAC_DISP", str(int(total_fac)))

out = r"C:\Users\Tin Ko Oo\Desktop\demo\mandalay_hotspot_webmap.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)

print(f"HTML size : {os.path.getsize(out)/1024:.0f} KB")
print(f"Saved     : {out}")
