# AquaHeat AI
Run: `run.bat` (Windows) or `sh run.sh`, then open http://127.0.0.1:5000 (do not double-click index.html).

## Honest scope
- Prototype ML model trained on simulated environmental stress data, designed to be replaceable with live datasets.
- Default mode is a demo scenario (peak heat stress). `USE_LIVE_DATA=1` blends real Open-Meteo temperature/rainfall into the inputs; vegetation, demand and density remain modelled.
- The 30-day view is a scenario-based risk projection, not a weather forecast.

## AI layer
Amazon Bedrock (Converse API, default model amazon.nova-lite-v1:0) -> Groq -> offline template.
Enable Bedrock model access in the AWS console, then put AWS credentials in `.env`.

## Data and AWS
- Fetch (Open-Meteo) -> Amazon S3 (`raw/`, `processed/`; local `./data` mirror if S3_BUCKET is empty) -> processing -> ML ensemble -> Amazon Bedrock -> agent -> dashboard.
- Vegetation is a soil-moisture/ET proxy when live, not NDVI. Water demand is a modelled estimate.
- Confidence = share of 240 ensemble x input-uncertainty draws that keep the same risk level.
- Demo: open http://127.0.0.1:5000/?demo=1 to auto-play the 30-second guided demo.

## SageMaker, Bedrock and methodology
- `python aws/deploy.py --role <arn> --bucket <bucket>` deploys the Nexus model as a SageMaker real-time endpoint; set `SAGEMAKER_ENDPOINT` in `.env`. If unset or unreachable the local model is used.
- The agent calls the Amazon Bedrock Converse API directly (not Bedrock Agents Classic).
- Open `/methodology` for data sources, model information and limitations.
- Rainfall slider fix: it now sends the % change in rainfall (negative = drier = higher risk).

## Amazon Bedrock AgentCore
`pip install -r agentcore/requirements.txt`, then `agentcore configure -e agentcore/agent.py` and `agentcore launch`. Put the agent ARN in `.env` as `AGENTCORE_RUNTIME_ARN`; the Flask app then calls the hosted agent via `invoke_agent_runtime` (order: AgentCore, Bedrock, Groq, offline). Use a recent boto3 (`pip install -U boto3`).

## Water-demand data
Reported Gurugram figures (GMDA/MCG via press) are in `/api/waterref` and on the Methodology page. They are press-reported, not meter data. Live mode anchors the Gurugram-area demand input to them; other locations remain modelled.

## Eight feature modules
City Survival Twin (`/api/twin`), Heat-Water Nexus with separate heat, flood and scarcity scores, AI Resilience Action Plan (`/api/actions`), What-If simulator (`/api/simulate`), Rainwater and flood-to-resource optimizer (`/api/harvest`), Water and leak intelligence (`/api/water`, `/api/anomaly`), Community alerts and reports (`/api/alerts`, `/api/reports`), Trust and explainability center (`/api/trust`). New endpoints live in `extras.py`.
- The model now has 5 inputs (groundwater stress added). If you deployed a SageMaker endpoint earlier, redeploy it with `python aws/deploy.py` so it matches.
- Community reports are saved to `data/reports.json` (temporary storage on Render).

## Smart location search
Search any place (Open-Meteo geocoding), then every dashboard section uses that place: `GET /api/locations/search?q=`, `GET /api/location-data?lat=&lon=`, `POST /api/location-risk`. Code: `geo.py`, `static/geo.js`.
- Data: Open-Meteo forecast (current, last 14 days, next 7 days), archive (10-year normals), flood (river discharge); Nominatim for "Use my location" labels. No API key is needed. `OPEN_METEO_API_KEY` (optional) stays server-side.
- Searched locations are held in server memory (up to 40, oldest evicted). If the server restarts, the page asks you to search again (404 `unknown_location`); it never falls back to another city.
- Model inputs are checked against the training ranges and clipped values are flagged. Groundwater is real only near the CGWB reference areas; elsewhere it is reported as unavailable and a neutral value is used with wider uncertainty.
- Tests: `python tests/test_geo.py` (simulated providers). Try the UI without internet: `python tests/serve_fake.py` then open http://127.0.0.1:5055.

## How the page behaves
1. On load nothing is selected: only the search bar, a "Demo data" button and a welcome card are shown.
2. **Search a place** (any city, district or locality): every section shows that place with real forecast data. Demo areas are not mixed in. Places searched in the same session are compared in the City Twin and shown on the map.
3. **Demo data**: pick Gurugram, Sector 57, Delhi, Noida, Faridabad, Manesar, Sohna or Dwarka. These are simulated Delhi NCR scenarios (the Demo/Live toggle appears only here).
4. Clicking a nav link before choosing either shows a hint instead of an empty section. "Use demo scenario" returns to demo data.

## Map tiles
The risk map uses OpenStreetMap tiles (no API key), darkened in CSS. Please respect the OSM tile usage policy; for heavy use set `MAP_TILE_URL` (and `MAP_TILE_ATTRIBUTION`, `MAP_TILE_DARKEN`) to a provider you have an account with. Keys in a tile URL are visible to browsers, so restrict them to your domain. The previous CARTO dark tiles now require an API key and were removed.

## API keys (summary)
- **Open-Meteo: no key needed.** Free for non-commercial use (about 10,000 calls a day, attribution required: CC BY 4.0). For commercial use, subscribe at https://open-meteo.com/en/pricing; you receive a key immediately. Put it in `OPEN_METEO_API_KEY`; the app then switches to the `customer-*` hosts automatically.
- Groq (`GROQ_API_KEY`), AWS (Bedrock, S3, SageMaker, AgentCore) and `MAP_TILE_URL` keys are all optional.
