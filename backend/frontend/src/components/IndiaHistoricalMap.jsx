import { useEffect, useMemo, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const API_BASE = "http://127.0.0.1:8000";
const INDIA_GEOJSON =
  "https://raw.githubusercontent.com/india-in-data/india-states-2019/master/india_states.geojson";

function fitIndia(map) {
  map.setView([22.5, 79], 4.3);
}

function IndiaHistoricalMap({ hazard = "Landslide" }) {
  const [geojson, setGeojson] = useState(null);
  const [risk, setRisk] = useState(null);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    fetch(INDIA_GEOJSON)
      .then((r) => r.json())
      .then(setGeojson)
      .catch(console.error);
  }, []);

  useEffect(() => {
    fetch(`${API_BASE}/api/historical-risk?hazard=${encodeURIComponent(hazard)}`)
      .then((r) => r.json())
      .then(setRisk)
      .catch(console.error);
    setSelected(null);
  }, [hazard]);

  const lookup = useMemo(() => {
    const m = {};
    for (const row of risk?.states || []) {
      m[row.state.toLowerCase()] = row;
    }
    return m;
  }, [risk]);

  const style = (feature) => {
    const name = String(feature?.properties?.ST_NM || "").toLowerCase();
    const row = lookup[name];

    if (!row) {
      return {
        fillOpacity: 0.12,
        weight: 1,
      };
    }

    const n = row.historical_index;
    return {
      fillOpacity: 0.72,
      weight: 1,
      fillColor:
        n >= 75 ? "#dc2626" :
        n >= 60 ? "#f97316" :
        n >= 40 ? "#eab308" :
        "#22c55e",
    };
  };

  const onEachFeature = (feature, layer) => {
    const name = feature?.properties?.ST_NM || "Unknown";
    const row = lookup[String(name).toLowerCase()];

    layer.bindTooltip(name, { sticky: true });

    layer.on({
      click: () => setSelected(row ? { name, ...row } : {
        name,
        category: "No comparable inventory coverage",
      }),
      mouseover: (e) => e.target.setStyle({ weight: 2 }),
      mouseout: (e) => e.target.setStyle(style(feature)),
    });
  };

  return (
    <section className="historical-risk-section">
      <div className="historical-risk-header">
        <div>
          <div className="eyebrow">INDIA HISTORICAL EVIDENCE</div>
          <h2>Where has this hazard actually occurred?</h2>
          <p>
            This layer uses historical disaster inventories instead of the
            synthetic village risk formula.
          </p>
        </div>

        {selected && (
          <div className="historical-selected-card">
            <strong>{selected.name}</strong>
            <div>{selected.category}</div>
            {selected.historical_count !== undefined && (
              <div>
                Recorded inventory:{" "}
                {Number(selected.historical_count).toLocaleString("en-IN")}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="historical-map-wrap">
        <MapContainer
          center={[22.5, 79]}
          zoom={4}
          scrollWheelZoom={false}
          style={{ height: "620px", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {geojson && (
            <GeoJSON
              data={geojson}
              style={style}
              onEachFeature={onEachFeature}
            />
          )}
        </MapContainer>
      </div>

      <div className="historical-legend">
        <span><i className="legend-dot critical" /> Critical</span>
        <span><i className="legend-dot high" /> High</span>
        <span><i className="legend-dot moderate" /> Moderate</span>
        <span><i className="legend-dot low" /> Low</span>
        <span><i className="legend-dot uncovered" /> Not covered by this inventory</span>
      </div>

      <p className="historical-disclaimer">
        Historical occurrence is not the same as future probability. A state
        without entries in this particular inventory must not be interpreted
        as disaster-free.
      </p>
    </section>
  );
}

export default IndiaHistoricalMap;
