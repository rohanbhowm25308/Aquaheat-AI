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
# Aquaheat-AI
