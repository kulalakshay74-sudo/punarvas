import { Fragment, useEffect, useMemo, useState } from "react";
import {
  Circle,
  CircleMarker,
  MapContainer,
  Polyline,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "./App.css";
import IndiaHistoricalMap from "./components/IndiaHistoricalMap";
import "./historical-risk.css";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const HAZARDS = ["Flood", "Landslide", "Coastal Erosion", "Cloudburst"];

function riskColor(score) {
  const value = Number(score || 0);
  if (value >= 75) return "#b91c1c";
  if (value >= 60) return "#ea580c";
  if (value >= 40) return "#ca8a04";
  return "#16a34a";
}

function priorityColor(priority) {
  if (priority === "Immediate") return "#b91c1c";
  if (priority === "Short-term") return "#ea580c";
  return "#2563eb";
}

function formatError(detail) {
  if (!detail) return "An unknown error occurred.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((x) => x?.msg || String(x)).join(" | ");
  if (detail.message) return detail.message;
  return JSON.stringify(detail);
}

function MapController({ selectedVillage }) {
  const map = useMap();
  useEffect(() => {
    if (selectedVillage) {
      map.flyTo(
        [Number(selectedVillage.Latitude), Number(selectedVillage.Longitude)],
        10,
        { duration: 0.8 }
      );
    }
  }, [selectedVillage, map]);
  return null;
}

function Metric({ title, value, subtitle }) {
  return (
    <div className="metric-card">
      <span>{title}</span>
      <strong>{value}</strong>
      {subtitle && <small>{subtitle}</small>}
    </div>
  );
}

function ScoreBar({ label, value }) {
  const score = Math.max(0, Math.min(100, Number(value || 0)));
  return (
    <div className="score-row">
      <div><span>{label}</span><strong>{score.toFixed(1)}</strong></div>
      <div className="score-track"><i style={{ width: `${score}%` }} /></div>
    </div>
  );
}

function App() {
  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [selectedVillage, setSelectedVillage] = useState(null);
  const [sites, setSites] = useState([]);
  const [hazardFilter, setHazardFilter] = useState("All hazards");
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [targetPopulation, setTargetPopulation] = useState(850);
  const [budget, setBudget] = useState(20000000);
  const [relocation, setRelocation] = useState(null);
  const [relocationLoading, setRelocationLoading] = useState(false);
  const [relocationError, setRelocationError] = useState("");

  const villages = analysis?.villages || [];

  const visibleVillages = useMemo(() => {
    if (hazardFilter === "All hazards") return villages;
    return villages.filter((v) => Number(v.HazardScores?.[hazardFilter] || 0) >= 60);
  }, [villages, hazardFilter]);

  const redZones = villages.filter((v) => v.IsRedZone);
  const immediate = villages.filter((v) => v.PriorityCategory === "Immediate");
  const shortTerm = villages.filter((v) => v.PriorityCategory === "Short-term");
  const mediumTerm = villages.filter((v) => v.PriorityCategory === "Medium-term");

  const mapCenter = selectedVillage
    ? [Number(selectedVillage.Latitude), Number(selectedVillage.Longitude)]
    : villages.length
      ? [Number(villages[0].Latitude), Number(villages[0].Longitude)]
      : [13.05, 75.35];

  const recommendedSite = relocation?.recommended_site;
  const route = selectedVillage && recommendedSite
    ? [
        [Number(selectedVillage.Latitude), Number(selectedVillage.Longitude)],
        [Number(recommendedSite.latitude), Number(recommendedSite.longitude)],
      ]
    : [];

  function selectVillage(village) {
    setSelectedVillage(village);
    setTargetPopulation(Number(village.Population));
    setRelocation(null);
    setRelocationError("");
  }

  async function runAnalysis({ silent = false } = {}) {
    if (!file) {
      setError("Upload the village CSV first.");
      return;
    }

    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(formatError(data.detail));

      setAnalysis(data);
      setLastUpdated(data.updated_at);

      setSelectedVillage((current) => {
        if (!current) return data.villages?.[0] || null;
        return data.villages?.find((v) => v.Village === current.Village) || data.villages?.[0] || null;
      });
    } catch (err) {
      setError(err.message || "Unable to connect to PUNARVAS backend.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  async function loadSites(population = targetPopulation) {
    try {
      const response = await fetch(`${API_BASE}/api/safe-sites?target_population=${Number(population) || 0}`);
      const data = await response.json();
      if (!response.ok) throw new Error(formatError(data.detail));
      setSites(data.sites || []);
    } catch (err) {
      setError(err.message || "Unable to assess safer sites.");
    }
  }

  async function runRelocation() {
    if (!selectedVillage) {
      setRelocationError("Select a habitation first.");
      return;
    }

    setRelocationLoading(true);
    setRelocationError("");
    setRelocation(null);

    try {
      const formData = new FormData();
      formData.append("source_village", selectedVillage.Village);
      formData.append("target_population", String(Number(targetPopulation)));
      formData.append("budget", String(Number(budget)));
      formData.append("hazard", hazardFilter === "All hazards" ? "Flood" : hazardFilter);
      formData.append("risk_score", String(Number(selectedVillage.HazardIntensity || 0)));

      const response = await fetch(`${API_BASE}/api/relocate`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(formatError(data.detail));
      setRelocation(data);
      await loadSites(targetPopulation);
    } catch (err) {
      setRelocationError(err.message || "Relocation assessment failed.");
    } finally {
      setRelocationLoading(false);
    }
  }

  useEffect(() => {
    if (!analysis) return undefined;
    const timer = setInterval(() => runAnalysis({ silent: true }), 30000);
    return () => clearInterval(timer);
  }, [analysis, file]);

  useEffect(() => {
    if (analysis) loadSites(targetPopulation);
  }, [analysis, targetPopulation]);

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <div className="brand">PUNARVAS</div>
          <div className="brand-subtitle">AI-Driven GIS Platform for Proactive Disaster Relocation</div>
        </div>
        <div className="live-status"><i /> DYNAMIC DECISION SUPPORT</div>
      </header>

      <main className="dashboard">
        <section className="hero">
          <div>
            <div className="eyebrow">SMART INDIA HACKATHON 2026 · PS 26191</div>
            <h1>Hazard-Based Red Zones, Carrying Capacity & Relocation Needs</h1>
            <p>
              PUNARVAS dynamically maps multi-hazard Red Zones, assesses safer relocation sites and their carrying capacity, and prioritizes vulnerable habitations using hazard intensity, population vulnerability and disaster history.
            </p>
          </div>
          <div className="refresh-box">
            <span>DATA STATUS</span>
            <strong>{lastUpdated ? "Updated" : "Waiting for analysis"}</strong>
            <small>{lastUpdated ? new Date(lastUpdated).toLocaleString("en-IN") : "—"}</small>
            {analysis && <button onClick={() => runAnalysis({ silent: true })} disabled={refreshing}>{refreshing ? "Refreshing…" : "Refresh now"}</button>}
          </div>
        </section>

        <section className="control-panel">
          <div className="control-group upload-group">
            <label>Village / GIS Input</label>
            <input type="file" accept=".csv" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            {file && <small>{file.name}</small>}
          </div>
          <div className="control-group">
            <label>Map hazard layer</label>
            <select value={hazardFilter} onChange={(e) => setHazardFilter(e.target.value)}>
              <option>All hazards</option>
              {HAZARDS.map((hazard) => <option key={hazard}>{hazard}</option>)}
            </select>
          </div>
          <button className="primary-button" onClick={() => runAnalysis()} disabled={loading}>
            {loading ? "Analyzing…" : "Analyze PUNARVAS"}
          </button>
        </section>

        <div className="data-note">
          Required input: Village, Latitude, Longitude, Population, Elevation, RoadDistance, Rainfall, DistanceFromRiver, DistanceFromCoast, Slope, Infrastructure, PopulationVulnerability, DisasterHistory.
        </div>

        {error && <div className="error-box"><strong>System message:</strong> {error}</div>}

        {analysis && (
          <>
            <section className="metrics-grid">
              <Metric title="Habitations" value={analysis.summary.total_villages} />
              <Metric title="Population" value={analysis.summary.total_population.toLocaleString("en-IN")} />
              <Metric title="Red Zones" value={analysis.summary.red_zones} subtitle="Unsuitable for permanent habitation" />
              <Metric title="Immediate" value={analysis.summary.immediate} subtitle="Relocation need" />
              <Metric title="Short-term" value={analysis.summary.short_term} subtitle="Relocation need" />
              <Metric title="Medium-term" value={analysis.summary.medium_term} subtitle="Relocation need" />
            </section>

            <section className="section-card">
              <div className="section-heading">
                <div>
                  <div className="eyebrow">1 · MULTI-HAZARD RED ZONES</div>
                  <h2>Dynamic GIS hazard map</h2>
                  <p>Red Zones are recalculated from the four hazard layers whenever the analysis refreshes.</p>
                </div>
                <div className="legend-inline">
                  <span><i className="dot red" /> Red Zone</span>
                  <span><i className="dot orange" /> High priority</span>
                  <span><i className="dot blue" /> Safer site</span>
                </div>
              </div>

              <div className="map-container large-map">
                <MapContainer center={mapCenter} zoom={9} scrollWheelZoom style={{ height: "100%", width: "100%" }}>
                  <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                  <MapController selectedVillage={selectedVillage} />

                  {visibleVillages.map((village) => {
                    const isRed = village.IsRedZone;
                    const score = hazardFilter === "All hazards"
                      ? village.HazardIntensity
                      : village.HazardScores?.[hazardFilter] || 0;
                    return (
                      <Fragment key={village.Village}>
                        {isRed && (
                          <Circle
                            center={[Number(village.Latitude), Number(village.Longitude)]}
                            radius={1800}
                            pathOptions={{ color: "#dc2626", fillColor: "#dc2626", fillOpacity: 0.16, weight: 2 }}
                          />
                        )}
                        <CircleMarker
                          center={[Number(village.Latitude), Number(village.Longitude)]}
                          radius={selectedVillage?.Village === village.Village ? 12 : 8}
                          pathOptions={{ color: riskColor(score), fillColor: riskColor(score), fillOpacity: 0.9, weight: 3 }}
                          eventHandlers={{ click: () => selectVillage(village) }}
                        >
                          <Popup>
                            <strong>{village.Village}</strong><br />
                            Hazard intensity: {Number(village.HazardIntensity).toFixed(1)}<br />
                            Red Zone: {isRed ? "Yes" : "No"}<br />
                            Priority: {village.PriorityCategory}
                          </Popup>
                        </CircleMarker>
                      </Fragment>
                    );
                  })}

                  {recommendedSite && (
                    <CircleMarker
                      center={[Number(recommendedSite.latitude), Number(recommendedSite.longitude)]}
                      radius={13}
                      pathOptions={{ color: "#2563eb", fillColor: "#2563eb", fillOpacity: 0.9, weight: 4 }}
                    >
                      <Popup>
                        <strong>Safer relocation site</strong><br />
                        {recommendedSite.site}<br />
                        Suitability: {recommendedSite.safety_score}<br />
                        Carrying capacity: {recommendedSite.capacity}
                      </Popup>
                    </CircleMarker>
                  )}

                  {route.length === 2 && <Polyline positions={route} pathOptions={{ color: "#2563eb", weight: 4, dashArray: "8 8" }} />}
                </MapContainer>
              </div>

              <div className="hazard-summary-grid">
                {HAZARDS.map((hazard) => {
                  const count = villages.filter((v) => Number(v.HazardScores?.[hazard] || 0) >= 75).length;
                  return <div key={hazard}><span>{hazard}</span><strong>{count}</strong><small>Red Zone threshold</small></div>;
                })}
              </div>
            </section>

            <section className="two-column">
              <div className="section-card">
                <div className="section-heading compact">
                  <div>
                    <div className="eyebrow">2 · HABITATION PRIORITIZATION</div>
                    <h2>Who needs relocation first?</h2>
                    <p>Priority integrates hazard intensity, population vulnerability and disaster history.</p>
                  </div>
                </div>
                <div className="priority-cards">
                  <div><span>Immediate</span><strong>{immediate.length}</strong></div>
                  <div><span>Short-term</span><strong>{shortTerm.length}</strong></div>
                  <div><span>Medium-term</span><strong>{mediumTerm.length}</strong></div>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead><tr><th>Habitation</th><th>Population</th><th>Hazard</th><th>Vulnerability</th><th>History</th><th>Priority</th></tr></thead>
                    <tbody>
                      {[...villages].sort((a, b) => b.PriorityScore - a.PriorityScore).map((village) => (
                        <tr key={village.Village} onClick={() => selectVillage(village)}>
                          <td><strong>{village.Village}</strong></td>
                          <td>{Number(village.Population).toLocaleString("en-IN")}</td>
                          <td>{Number(village.HazardIntensity).toFixed(1)}</td>
                          <td>{Number(village.PopulationVulnerability).toFixed(1)}</td>
                          <td>{Number(village.DisasterHistory).toFixed(1)}</td>
                          <td><b style={{ color: priorityColor(village.PriorityCategory) }}>{village.PriorityCategory}</b></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="section-card">
                <div className="section-heading compact">
                  <div>
                    <div className="eyebrow">3 · HABITATION DECISION</div>
                    <h2>{selectedVillage ? selectedVillage.Village : "Select a habitation"}</h2>
                    <p>Evidence behind the relocation priority.</p>
                  </div>
                </div>
                {selectedVillage ? (
                  <>
                    <div className="decision-score">
                      <div><span>Priority score</span><strong>{Number(selectedVillage.PriorityScore).toFixed(1)}</strong></div>
                      <b style={{ color: priorityColor(selectedVillage.PriorityCategory) }}>{selectedVillage.PriorityCategory}</b>
                    </div>
                    <ScoreBar label="Hazard intensity" value={selectedVillage.HazardIntensity} />
                    <ScoreBar label="Population vulnerability" value={selectedVillage.PopulationVulnerability} />
                    <ScoreBar label="Disaster history" value={selectedVillage.DisasterHistory} />
                    <div className="hazard-list">
                      {HAZARDS.map((hazard) => <div key={hazard}><span>{hazard}</span><strong>{Number(selectedVillage.HazardScores?.[hazard] || 0).toFixed(1)}</strong></div>)}
                    </div>
                    <div className="action-box">
                      <strong>Actionable insight</strong>
                      <p>
                        {selectedVillage.Village} is classified for <b>{selectedVillage.PriorityCategory.toLowerCase()}</b> relocation planning based on integrated hazard intensity, population vulnerability and disaster history.
                      </p>
                    </div>
                  </>
                ) : <div className="empty-state">Select a habitation from the table or map.</div>}
              </div>
            </section>

            <section className="section-card">
              <div className="section-heading">
                <div>
                  <div className="eyebrow">4 · SAFER ALTERNATIVE SITES</div>
                  <h2>Suitability and carrying capacity</h2>
                  <p>Each safer site is assessed for suitability and how much population it can support.</p>
                </div>
              </div>
              <div className="site-grid">
                {sites.map((site) => (
                  <div className="site-card" key={site.site}>
                    <div className="site-card-top"><h3>{site.site}</h3><b>{site.suitability_score}/100</b></div>
                    <div className="site-facts">
                      <div><span>Suitability</span><strong>{site.suitability_score}</strong></div>
                      <div><span>Carrying capacity</span><strong>{Number(site.carrying_capacity).toLocaleString("en-IN")}</strong></div>
                      <div><span>Available for target</span><strong>{Number(site.available_capacity).toLocaleString("en-IN")}</strong></div>
                      <div><span>Status</span><strong>{site.capacity_status}</strong></div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="section-card relocation-section">
              <div className="section-heading">
                <div>
                  <div className="eyebrow">5 · RELOCATION DECISION</div>
                  <h2>From vulnerable habitation to safer site</h2>
                  <p>Use the assessed safer sites, carrying capacity and available budget to produce a relocation recommendation.</p>
                </div>
              </div>
              <div className="relocation-controls">
                <label>Selected habitation<input value={selectedVillage?.Village || ""} readOnly /></label>
                <label>Population to relocate<input type="number" value={targetPopulation} onChange={(e) => setTargetPopulation(e.target.value)} /></label>
                <label>Available budget (₹)<input type="number" value={budget} onChange={(e) => setBudget(e.target.value)} /></label>
                <button className="primary-button" onClick={runRelocation} disabled={relocationLoading || !selectedVillage}>{relocationLoading ? "Assessing…" : "Assess relocation"}</button>
              </div>
              {relocationError && <div className="error-box">{relocationError}</div>}
              {relocation?.recommended_site && (
                <div className="recommended-card">
                  <div><span>Recommended safer site</span><strong>{relocation.recommended_site.site}</strong></div>
                  <div><span>Suitability</span><strong>{relocation.recommended_site.safety_score}</strong></div>
                  <div><span>Carrying capacity</span><strong>{Number(relocation.recommended_site.capacity).toLocaleString("en-IN")}</strong></div>
                  <div><span>Distance</span><strong>{relocation.recommended_site.distance_km} km</strong></div>
                  <div><span>Total relocation cost</span><strong>₹{Number(relocation.recommended_site.total_cost).toLocaleString("en-IN")}</strong></div>
                </div>
              )}
              {relocation?.status === "no_feasible_solution" && <div className="action-box"><strong>No feasible safer site under current constraints.</strong><p>{relocation.message}</p></div>}
            </section>

            <section className="section-card">
              <div className="section-heading compact">
                <div>
                  <div className="eyebrow">6 · DISASTER HISTORY EVIDENCE</div>
                  <h2>Historical occurrence context</h2>
                  <p>Historical disaster records are used as evidence for prioritization; they are not treated as a guarantee of future safety.</p>
                </div>
              </div>
              <IndiaHistoricalMap hazard={hazardFilter === "All hazards" ? "Landslide" : hazardFilter} />
            </section>
          </>
        )}
      </main>

      <footer className="footer">PUNARVAS · Problem Statement 26191 · GIS Decision Support for Proactive Disaster Relocation</footer>
    </div>
  );
}

export default App;
