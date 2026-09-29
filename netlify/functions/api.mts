import type { Config, Context } from "@netlify/functions";
import { readFile } from "node:fs/promises";
import path from "node:path";

const HAZARDS = ["Flood", "Landslide", "Coastal Erosion", "Cloudburst"];
const RED_ZONE_THRESHOLD = 60;
const IMMEDIATE_THRESHOLD = 75;
const SHORT_TERM_THRESHOLD = 50;

const WEIGHTS: Record<string, Record<string, number>> = {
  Flood: { HazardExposure: 0.35, PopulationVulnerability: 0.20, InfrastructureExposure: 0.20, AccessibilityRisk: 0.15, TerrainRisk: 0.10 },
  Landslide: { HazardExposure: 0.20, PopulationVulnerability: 0.15, InfrastructureExposure: 0.15, AccessibilityRisk: 0.15, TerrainRisk: 0.35 },
  "Coastal Erosion": { HazardExposure: 0.35, PopulationVulnerability: 0.25, InfrastructureExposure: 0.25, AccessibilityRisk: 0.10, TerrainRisk: 0.05 },
  Cloudburst: { HazardExposure: 0.30, PopulationVulnerability: 0.20, InfrastructureExposure: 0.20, AccessibilityRisk: 0.20, TerrainRisk: 0.10 },
};

function clamp(value: number, min = 0, max = 100) { return Math.max(min, Math.min(max, value)); }
function num(value: unknown, fallback = 0) { const n = Number(value); return Number.isFinite(n) ? n : fallback; }
function normalizeInverse(value: number, safe: number, dangerous: number) { return dangerous === safe ? 50 : clamp(((value - safe) / (dangerous - safe)) * 100); }
function normalizeDirect(value: number, safe: number, dangerous: number) { return dangerous === safe ? 50 : clamp(((value - safe) / (dangerous - safe)) * 100); }
function proximityRisk(value: number, safe: number, dangerous: number) { return dangerous === safe ? 50 : clamp(((safe - value) / (safe - dangerous)) * 100); }
function populationVulnerability(population: number) { return clamp(((population - 100) / (5000 - 100)) * 100); }
function terrainRisk(elevation: number, slope: number) {
  const slopeScore = normalizeDirect(slope, 2, 45);
  const elevationScore = normalizeInverse(elevation, 100, 1000);
  return Number(clamp(slopeScore * 0.75 + elevationScore * 0.25).toFixed(2));
}
function hazardExposure(row: any, hazard: string) {
  const rainfall = num(row.Rainfall), river = num(row.DistanceFromRiver), elevation = num(row.Elevation), slope = num(row.Slope), coast = num(row.DistanceFromCoast), road = num(row.RoadDistance);
  if (hazard === "Flood") return Number(clamp(normalizeDirect(rainfall, 500, 4000) * 0.45 + proximityRisk(river, 20, 0.5) * 0.40 + normalizeInverse(elevation, 50, 1000) * 0.15).toFixed(2));
  if (hazard === "Landslide") return Number(clamp(normalizeDirect(rainfall, 500, 4000) * 0.35 + normalizeDirect(slope, 2, 45) * 0.50 + normalizeDirect(elevation, 50, 1200) * 0.15).toFixed(2));
  if (hazard === "Coastal Erosion") return Number(clamp(proximityRisk(coast, 100, 0) * 0.75 + normalizeDirect(rainfall, 500, 4000) * 0.25).toFixed(2));
  return Number(clamp(normalizeDirect(rainfall, 500, 5000) * 0.55 + proximityRisk(river, 20, 0.5) * 0.25 + normalizeInverse(road, 1, 50) * 0.20).toFixed(2));
}
function calculateFeatures(row: any, hazard: string) {
  return { HazardExposure: hazardExposure(row, hazard), PopulationVulnerability: num(row.PopulationVulnerability, populationVulnerability(num(row.Population))), InfrastructureExposure: clamp(num(row.Infrastructure)), AccessibilityRisk: normalizeInverse(num(row.RoadDistance), 1, 50), TerrainRisk: terrainRisk(num(row.Elevation), num(row.Slope)) };
}
function riskCategory(score: number) { return score >= 75 ? "Critical" : score >= 60 ? "High" : score >= 40 ? "Moderate" : "Low"; }
function analyzeVillage(row: any) {
  const hazardScores: Record<string, number> = {}, hazardCategories: Record<string, string> = {};
  for (const hazard of HAZARDS) {
    const f = calculateFeatures(row, hazard), w = WEIGHTS[hazard];
    const score = f.HazardExposure*w.HazardExposure + f.PopulationVulnerability*w.PopulationVulnerability + f.InfrastructureExposure*w.InfrastructureExposure + f.AccessibilityRisk*w.AccessibilityRisk + f.TerrainRisk*w.TerrainRisk;
    hazardScores[hazard] = f.HazardExposure; hazardCategories[hazard] = riskCategory(score);
  }
  const vulnerability = clamp(num(row.PopulationVulnerability, populationVulnerability(num(row.Population))));
  const history = clamp(num(row.DisasterHistory, num(row.HistoricalRisk)));
  const hazardIntensity = Math.max(...Object.values(hazardScores));
  const priorityScore = Number(((hazardIntensity + vulnerability + history) / 3).toFixed(2));
  const redHazards = HAZARDS.filter(h => hazardScores[h] >= RED_ZONE_THRESHOLD);
  return { ...row, Latitude:num(row.Latitude), Longitude:num(row.Longitude), Population:num(row.Population), Elevation:num(row.Elevation), RoadDistance:num(row.RoadDistance), Rainfall:num(row.Rainfall), DistanceFromRiver:num(row.DistanceFromRiver), DistanceFromCoast:num(row.DistanceFromCoast), Slope:num(row.Slope), Infrastructure:num(row.Infrastructure), PopulationVulnerability:Number(vulnerability.toFixed(2)), DisasterHistory:Number(history.toFixed(2)), HazardIntensity:Number(hazardIntensity.toFixed(2)), PriorityScore:priorityScore, PriorityCategory:priorityScore>=IMMEDIATE_THRESHOLD?"Immediate":priorityScore>=SHORT_TERM_THRESHOLD?"Short-term":"Medium-term", IsRedZone:redHazards.length>0, RedZoneHazards:redHazards, HazardScores:Object.fromEntries(HAZARDS.map(h=>[h,Number(hazardScores[h].toFixed(2))])), HazardCategories:hazardCategories };
}
function parseCsv(text: string) {
  const rows:string[][]=[]; let row:string[]=[], cell="", quoted=false;
  for(let i=0;i<text.length;i++){const ch=text[i]; if(ch==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}else if(ch===','&&!quoted){row.push(cell);cell="";}else if((ch==="\n"||ch==="\r")&&!quoted){if(ch==="\r"&&text[i+1]==="\n")i++;row.push(cell);if(row.some(v=>v.trim()!==""))rows.push(row);row=[];cell="";}else cell+=ch;}
  if(cell.length||row.length){row.push(cell);if(row.some(v=>v.trim()!==""))rows.push(row);}
  if(!rows.length)return[]; const headers=rows[0].map(h=>h.trim()); return rows.slice(1).map(r=>Object.fromEntries(headers.map((h,i)=>[h,(r[i]??"").trim()])));
}
async function dataFile(name:string){return readFile(path.resolve(process.cwd(),"backend",name),"utf8");}
async function loadCsv(name:string){return parseCsv(await dataFile(name));}
function validateVillages(rows:any[]){const required=["Village","Latitude","Longitude","Population","Elevation","RoadDistance","Rainfall","DistanceFromRiver","DistanceFromCoast","Slope","Infrastructure"];const missing=required.filter(c=>!rows.length||!(c in rows[0]));if(missing.length)throw new Error("CSV is missing required columns: "+missing.join(", "));}
function analyzeRows(rows:any[]){
  validateVillages(rows); const villages=rows.map(analyzeVillage), red=villages.filter(v=>v.IsRedZone);
  return {updated_at:new Date().toISOString(),hazards:HAZARDS,red_zone_threshold:RED_ZONE_THRESHOLD,priority_thresholds:{immediate:IMMEDIATE_THRESHOLD,short_term:SHORT_TERM_THRESHOLD},summary:{total_villages:villages.length,total_population:villages.reduce((s,v)=>s+num(v.Population),0),red_zones:red.length,immediate:villages.filter(v=>v.PriorityCategory==="Immediate").length,short_term:villages.filter(v=>v.PriorityCategory==="Short-term").length,medium_term:villages.filter(v=>v.PriorityCategory==="Medium-term").length},villages};
}
function assessSites(sites:any[],targetPopulation=0){const required=Math.max(0,Math.floor(num(targetPopulation)));return sites.map(row=>{const capacity=Math.floor(num(row.Capacity)),safety=Number(num(row.SafetyScore).toFixed(2));return{site:String(row.Site??"Unknown"),latitude:num(row.Latitude),longitude:num(row.Longitude),suitability_score:safety,carrying_capacity:capacity,available_capacity:Math.max(capacity-required,0),capacity_status:required<=0?"Available":capacity>=required?"Sufficient":"Insufficient",cost_per_person:num(row.CostPerPerson)}});}
function haversine(lat1:number,lon1:number,lat2:number,lon2:number){const R=6371,rad=Math.PI/180,dLat=(lat2-lat1)*rad,dLon=(lon2-lon1)*rad,a=Math.sin(dLat/2)**2+Math.cos(lat1*rad)*Math.cos(lat2*rad)*Math.sin(dLon/2)**2;return R*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a));}
async function relocate(sourceVillage:string,targetPopulation:number,budget:number,sourceRiskScore=0){
  const villages=await loadCsv("sample_villages.csv"),sites=await loadCsv("safe_sites.csv"),source=villages.find(v=>String(v.Village).toLowerCase()===String(sourceVillage).toLowerCase());
  if(!source)throw new Error("Village '"+sourceVillage+"' was not found."); if(targetPopulation<=0)throw new Error("Target population must be greater than zero."); if(targetPopulation>num(source.Population))throw new Error("Target population cannot exceed the village population ("+num(source.Population)+")."); if(budget<=0)throw new Error("Budget must be greater than zero.");
  const candidates=sites.flatMap(site=>{const capacity=Math.floor(num(site.Capacity)),safety=num(site.SafetyScore),cost=num(site.CostPerPerson),total=targetPopulation*cost;if(capacity<targetPopulation||total>budget)return[];const distance=haversine(num(source.Latitude),num(source.Longitude),num(site.Latitude),num(site.Longitude)),score=(100-safety)*.45+Math.min(distance,100)*.25+Math.min(cost/25000*100,100)*.30;return[{site:String(site.Site),latitude:num(site.Latitude),longitude:num(site.Longitude),capacity,safety_score:safety,distance_km:Number(distance.toFixed(2)),cost_per_person:cost,total_cost:Number(total.toFixed(2)),optimization_score:Number(score.toFixed(2))}]}).sort((a,b)=>a.optimization_score-b.optimization_score);
  if(!candidates.length)return{status:"no_feasible_solution",message:"No relocation site satisfies the population capacity and budget constraints.",source_village:sourceVillage,source_risk_score:sourceRiskScore,source_risk_category:riskCategory(sourceRiskScore),target_population:targetPopulation,budget,candidates:[]};
  return{status:"success",source_village:sourceVillage,source_risk_score:Number(sourceRiskScore.toFixed(2)),source_risk_category:riskCategory(sourceRiskScore),target_population:targetPopulation,budget,recommended_site:candidates[0],remaining_budget:Number((budget-candidates[0].total_cost).toFixed(2)),evaluated_sites:candidates};
}
function json(data:unknown,status=200){return new Response(JSON.stringify(data),{status,headers:{"content-type":"application/json; charset=utf-8"}});}
function errorResponse(message:string,status=400){return json({detail:message},status);}
function normalizeState(name:string){const aliases:Record<string,string>={"jammu & kashmir":"Jammu and Kashmir","jammu and kashmir":"Jammu and Kashmir",orissa:"Odisha",uttaranchal:"Uttarakhand",pondicherry:"Puducherry","andaman and nicobar":"Andaman and Nicobar Islands","andaman & nicobar":"Andaman and Nicobar Islands"};const clean=String(name).replace(/\s+/g," ").trim();return aliases[clean.toLowerCase()]||clean;}
async function historical(hazard:string){
  const h=hazard.toLowerCase();
  if(h==="landslide"){const rows=await loadCsv("data/historical/landslide_state_inventory.csv");return{hazard:"Landslide",layer_type:"historical_inventory",period:"1998-2022",source:"ISRO / NRSC Landslide Atlas of India",source_url:"https://www.isro.gov.in/Landslide_Atlas_India.html",coverage_note:"Historical landslide inventory. States outside the inventory are not automatically safe.",states:rows.map(r=>({state:normalizeState(r.State),historical_count:Math.floor(num(r.LandslideCount_1998_2022)),historical_index:num(r.HistoricalIndex),category:String(r.HistoricalCategory)}))};}
  if(h==="flood"){const rows=await loadCsv("data/historical/flood_state_history.csv");return{hazard:"Flood",layer_type:"historical_inventory",period:"1967-2023",source:"India Flood Inventory-Impacts / IMD",source_url:"https://zenodo.org/records/16994648",coverage_note:"Historical flood events from the India Flood Inventory. Historical occurrence does not represent future probability.",states:rows.map(r=>({state:normalizeState(r.State),historical_count:Math.floor(num(r.HistoricalFloodEvents)),years_affected:Math.floor(num(r.YearsAffected)),first_recorded_year:Math.floor(num(r.FirstRecordedYear)),last_recorded_year:Math.floor(num(r.LastRecordedYear)),historical_index:num(r.HistoricalIndex),category:String(r.HistoricalCategory)}))};}
  if(["coastal erosion","coastal","erosion"].includes(h))return{hazard:"Coastal Erosion",layer_type:"historical_source_pending",period:"Pending verified integration",source:"ISRO Shoreline Change Atlas",source_url:"https://www.isro.gov.in/",coverage_note:"Coastal historical data will be integrated from a verified shoreline-change source.",states:[]};
  if(["cloudburst","cloud burst"].includes(h))return{hazard:"Cloudburst",layer_type:"historical_source_pending",period:"Pending verified integration",source:"Official disaster records",coverage_note:"A verified historical cloudburst inventory will be integrated before displaying state-level values.",states:[]};
  return{hazard,layer_type:"not_available",period:null,source:null,states:[]};
}

export default async (req:Request,_context:Context)=>{
  try{
    const url=new URL(req.url),route=url.pathname.replace(/^\/api\/?/,"").replace(/\/$/,"");
    if(route===""||route==="health")return json({status:route==="health"?"healthy":"running",project:"PUNARVAS",problem_statement:"26191"});
    if(route==="hazards")return json({hazards:HAZARDS});
    if(route==="sample-villages"){const csv=await dataFile("sample_villages.csv");return new Response(csv,{headers:{"content-type":"text/csv; charset=utf-8","content-disposition":"inline; filename=sample_villages.csv"}});}
    if(route==="analyze"&&req.method==="POST"){const form=await req.formData(),file=form.get("file");if(!(file instanceof File)||!file.name.toLowerCase().endsWith(".csv"))return errorResponse("Please upload a CSV file.");const result=analyzeRows(parseCsv(await file.text()));return json({...result,filename:file.name,mode:"uploaded_village_data"});}
    if(route==="live-analysis"||route==="red-zones"||route==="priorities"){const result=analyzeRows(await loadCsv("raw_villages.csv"));if(route==="live-analysis")return json({...result,mode:"live_dataset_refresh",data_source:"raw_villages.csv"});if(route==="red-zones")return json({updated_at:result.updated_at,threshold:result.red_zone_threshold,zones:result.villages.filter(v=>v.IsRedZone).map(v=>({village:v.Village,latitude:v.Latitude,longitude:v.Longitude,hazard_intensity:v.HazardIntensity,hazards:v.RedZoneHazards,priority:v.PriorityCategory}))});return json({updated_at:result.updated_at,priorities:result.villages.map(v=>({village:v.Village,population:v.Population,hazard_intensity:v.HazardIntensity,population_vulnerability:v.PopulationVulnerability,disaster_history:v.DisasterHistory,priority_score:v.PriorityScore,priority:v.PriorityCategory})).sort((a,b)=>b.priority_score-a.priority_score)});}
    if(route==="safe-sites"&&req.method==="GET")return json({updated_at:new Date().toISOString(),sites:assessSites(await loadCsv("safe_sites.csv"),num(url.searchParams.get("target_population")))});
    if(route==="relocate"&&req.method==="POST"){const form=await req.formData();return json(await relocate(String(form.get("source_village")||""),num(form.get("target_population")),num(form.get("budget")),num(form.get("risk_score"))));}
    if(route==="historical-risk")return json(await historical(url.searchParams.get("hazard")||"Landslide"));
    return errorResponse("API route not found.",404);
  }catch(err:any){return errorResponse(err?.message||"Internal server error.",500);}
};
export const config:Config={path:["/api","/api/*"]};
