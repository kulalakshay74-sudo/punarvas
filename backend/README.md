# PUNARVAS Historical Risk Layer

This package adds a source-backed historical disaster layer.

## Bundled now
ISRO/NRSC Landslide Atlas of India (1998-2022):
- state totals from the atlas inventory table
- relative historical occurrence index
- historical category

The index is a relative occurrence index, NOT a probability of future disaster.
States not present in the inventory are marked as "not covered", not "safe".

## Official / research sources used
- ISRO/NRSC Landslide Atlas: https://www.isro.gov.in/Landslide_Atlas_India.html
- India Flood Atlas: https://github.com/wcl-iitgn/india-flood-atlas-data
- India Flood Inventory / IFI-Impacts: https://zenodo.org/records/16994648
- India state boundaries: https://github.com/india-in-data/india-states-2019

## Integration
1. Copy backend/services/historical_risk.py to:
   ~/punarvas/backend/services/historical_risk.py
2. Copy backend/data/historical/landslide_state_inventory.csv to:
   ~/punarvas/backend/data/historical/landslide_state_inventory.csv
3. Add the GET endpoint shown in the chat to backend/main.py.
4. Copy IndiaHistoricalMap.jsx to frontend/src/components/.
5. Import it in App.jsx and render:
   <IndiaHistoricalMap hazard={hazard} />
6. Import frontend/src/historical-risk.css from App.jsx or main.jsx.

Flood integration should use the India Flood Atlas / IFI-Impacts data rather than invented state scores.
