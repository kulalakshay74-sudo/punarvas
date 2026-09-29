import { useEffect, useMemo, useState } from "react";
import { GeoJSON, MapContainer, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const API_BASE = import.meta.env.VITE_API_URL || "";

const INDIA_GEOJSON =
  "https://raw.githubusercontent.com/india-in-data/india-states-2019/master/india_states.geojson";

function normalizeStateName(name) {
  return String(name || "")
    .toLowerCase()
    .trim()
    .replace(/&/g, "and")
    .replace(/[.,'’()-]/g, " ")
    .replace(/\s+/g, " ");
}

function getHistoricalColor(index) {
  if (index >= 75) return "#dc2626";
  if (index >= 60) return "#f97316";
  if (index >= 40) return "#eab308";
  return "#22c55e";
}

function IndiaHistoricalMap({ hazard = "Landslide" }) {
  const [geojson, setGeojson] = useState(null);
  const [risk, setRisk] = useState(null);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(INDIA_GEOJSON)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Unable to load India state boundaries.");
        }
        return response.json();
      })
      .then((data) => {
        setGeojson(data);
      })
      .catch((err) => {
        console.error(err);
        setError("Unable to load India map boundaries.");
      });
  }, []);

  useEffect(() => {
    setSelected(null);
    setError("");

    fetch(
      `${API_BASE}/api/historical-risk?hazard=${encodeURIComponent(hazard)}`
    )
      .then((response) => {
        if (!response.ok) {
          throw new Error("Historical risk API failed.");
        }
        return response.json();
      })
      .then((data) => {
        setRisk(data);
      })
      .catch((err) => {
        console.error(err);
        setError("Unable to load historical disaster data.");
      });
  }, [hazard]);

  const lookup = useMemo(() => {
    const map = {};

    for (const row of risk?.states || []) {
      map[normalizeStateName(row.state)] = row;
    }

    return map;
  }, [risk]);

  const getRowForFeature = (feature) => {
    const possibleNames = [
      feature?.properties?.ST_NM,
      feature?.properties?.NAME_1,
      feature?.properties?.NAME,
      feature?.properties?.State,
      feature?.properties?.state,
    ];

    for (const name of possibleNames) {
      const normalized = normalizeStateName(name);

      if (lookup[normalized]) {
        return {
          name,
          row: lookup[normalized],
        };
      }
    }

    return {
      name: possibleNames.find(Boolean) || "Unknown",
      row: null,
    };
  };

  const style = (feature) => {
    const { row } = getRowForFeature(feature);

    if (!row) {
      return {
        fillColor: "#cbd5e1",
        fillOpacity: 0.18,
        color: "#64748b",
        weight: 1,
      };
    }

    return {
      fillColor: getHistoricalColor(Number(row.historical_index)),
      fillOpacity: 0.72,
      color: "#ffffff",
      weight: 1,
    };
  };

  const onEachFeature = (feature, layer) => {
    const { name, row } = getRowForFeature(feature);

    layer.bindTooltip(name, {
      sticky: true,
    });

    layer.on({
      click: () => {
        if (row) {
          setSelected({
            name: row.state,
            ...row,
          });
        } else {
          setSelected({
            name,
            category: "No comparable inventory coverage",
          });
        }
      },

      mouseover: (event) => {
        event.target.setStyle({
          weight: 3,
          color: "#111827",
        });
      },

      mouseout: (event) => {
        event.target.setStyle(style(feature));
      },
    });
  };

  return (
    <section className="historical-risk-section">

      <div className="historical-risk-header">

        <div>
          <div className="eyebrow">
            INDIA HISTORICAL EVIDENCE
          </div>

          <h2>
            Where has this hazard actually occurred?
          </h2>

          <p>
            This layer uses historical disaster inventories
            instead of the synthetic village risk formula.
          </p>
        </div>

        {selected && (
          <div className="historical-selected-card">

            <strong>
              {selected.name}
            </strong>

            <div className="selected-category">
              {selected.category}
            </div>

            {selected.historical_count !== undefined && (
              <>
                <div>
                  Historical occurrences:{" "}
                  {Number(
                    selected.historical_count
                  ).toLocaleString("en-IN")}
                </div>

                <div>
                  Historical index:{" "}
                  {Number(
                    selected.historical_index
                  ).toFixed(2)}
                </div>

                <div>
                  Period:{" "}
                  {risk?.period || "Historical inventory"}
                </div>
              </>
            )}
          </div>
        )}

      </div>

      {error && (
        <div className="historical-error">
          {error}
        </div>
      )}

      <div className="historical-map-wrap">

        <MapContainer
          center={[22.5, 79]}
          zoom={4}
          scrollWheelZoom={false}
          style={{
            height: "620px",
            width: "100%",
          }}
        >

          <TileLayer
            attribution="&copy; OpenStreetMap contributors"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {geojson && (
            <GeoJSON
              key={`${hazard}-${risk?.period || ""}`}
              data={geojson}
              style={style}
              onEachFeature={onEachFeature}
            />
          )}

        </MapContainer>

      </div>

      <div className="historical-legend">

        <span>
          <i className="legend-dot critical" />
          Critical (≥75)
        </span>

        <span>
          <i className="legend-dot high" />
          High (60–74.99)
        </span>

        <span>
          <i className="legend-dot moderate" />
          Moderate (40–59.99)
        </span>

        <span>
          <i className="legend-dot low" />
          Lower occurrence (&lt;40)
        </span>

        <span>
          <i className="legend-dot uncovered" />
          No comparable inventory
        </span>

      </div>

      <div className="historical-source">

        <strong>
          Historical source:
        </strong>{" "}

        {risk?.source || "Historical disaster inventory"}

        {risk?.period && (
          <>
            {" "}({risk.period})
          </>
        )}

      </div>

      <p className="historical-disclaimer">

        Historical occurrence is not the same as future
        probability. A state without entries in this
        particular inventory must not be interpreted as
        disaster-free.

      </p>

    </section>
  );
}

export default IndiaHistoricalMap;
