# PUNARVAS — SIH 2026 Problem Statement 26191

PUNARVAS is a GIS-enabled decision-support prototype for proactive disaster relocation.

## Implemented PS 26191 scope

1. Dynamic multi-hazard Red Zone mapping for:
   - Flood
   - Landslide
   - Coastal erosion
   - Cloudburst
2. Safer alternative site assessment:
   - suitability score
   - carrying capacity
   - available capacity for the target population
3. Vulnerable habitation prioritization using:
   - hazard intensity
   - population vulnerability
   - disaster history
4. Relocation classification:
   - Immediate
   - Short-term
   - Medium-term
5. GIS map and actionable decision output for authorities.
6. Dynamic re-evaluation on refresh and automatic 30-second recalculation while the dashboard is open.

## Important prototype note

The scoring engine is transparent and rule-based so that the factors behind every decision can be inspected. It is not a trained machine-learning model and the demo rules are not a scientifically validated hazard forecast. Live operational deployment would replace the demo CSV inputs with validated live/near-real-time government and geospatial feeds.

## Backend

```text
cd backend
python -m venv venv
# activate venv
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend: `http://127.0.0.1:8000`

## Frontend

```text
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

Optional `.env`:

```text
VITE_API_URL=http://127.0.0.1:8000
```

## Village data columns

```text
Village
Latitude
Longitude
Population
Elevation
RoadDistance
Rainfall
DistanceFromRiver
DistanceFromCoast
Slope
Infrastructure
PopulationVulnerability
DisasterHistory
```
