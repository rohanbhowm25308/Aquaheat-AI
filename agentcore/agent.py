"""AquaHeat Intelligence on Amazon Bedrock AgentCore Runtime.
Deploy:  pip install -r agentcore/requirements.txt
         agentcore configure -e agentcore/agent.py     (choose your region and an execution role)
         agentcore launch
Then put the printed agent ARN in .env as AGENTCORE_RUNTIME_ARN (and bedrock-agentcore:InvokeAgentRuntime permission on your user/role).
Model access: enable your chosen model in the Bedrock console; set AGENT_MODEL_ID to override the Strands default."""
import os
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent, tool

app = BedrockAgentCoreApp()

@tool
def water_gap(demand_mld: float, supply_mld: float) -> str:
    """Compute the water supply gap in million litres per day and as a percent of supply."""
    gap = demand_mld - supply_mld
    return f"Gap {gap:.0f} MLD ({gap / supply_mld * 100:.1f}% of supply)"

@tool
def risk_band(nexus: float) -> str:
    """Map a 0-100 Nexus score to AquaHeat's risk level (LOW <35, MODERATE <55, HIGH <75, CRITICAL otherwise)."""
    return "LOW" if nexus < 35 else "MODERATE" if nexus < 55 else "HIGH" if nexus < 75 else "CRITICAL"

SYSTEM = ("You are AquaHeat Intelligence, an environmental decision-support agent for heat and water stress. "
          "Use only the model output given in the prompt; never invent numbers. Use tools for arithmetic and risk bands. "
          "Follow the output format requested in the prompt exactly.")
kwargs = {"system_prompt": SYSTEM, "tools": [water_gap, risk_band]}
if os.getenv("AGENT_MODEL_ID"):
    from strands.models import BedrockModel
    kwargs["model"] = BedrockModel(model_id=os.environ["AGENT_MODEL_ID"])
agent = Agent(**kwargs)

@app.entrypoint
def invoke(payload):
    result = agent(payload.get("prompt", ""))
    return {"result": str(result)}

if __name__ == "__main__":
    app.run()
