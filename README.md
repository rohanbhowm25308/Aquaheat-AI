#  AquaHeat AI

### Predict Heat. Protect Water. Prevent Crisis.

**An AI-powered environmental intelligence platform connecting heat-risk analysis, water resilience, and interactive climate simulations.**

\<p align="center">
&#x20; \<a href="[https://aquaheat-ai.onrender.com/](https://aquaheat-ai.onrender.com/)">\<strong>🚀 Live Demo\</strong>\</a> •
&#x20; \<a href="[https://github.com/rohanbhowm25308/Aquaheat-AI](https://github.com/rohanbhowm25308/Aquaheat-AI)">\<strong>💻 Source Code\</strong>\</a>
\</p>

\<p align="center">
&#x20; \<img src="[https://img.shields.io/badge/AI-Environmental%20Intelligence-00C9D8?style=for-the-badge](https://img.shields.io/badge/AI-Environmental%20Intelligence-00C9D8?style=for-the-badge)" alt="Environmental Intelligence">
&#x20; \<img src="[https://img.shields.io/badge/ML-scikit--learn-orange?style=for-the-badge](https://img.shields.io/badge/ML-scikit--learn-orange?style=for-the-badge)" alt="Machine Learning">
&#x20; \<img src="[https://img.shields.io/badge/Backend-Flask-black?style=for-the-badge](https://img.shields.io/badge/Backend-Flask-black?style=for-the-badge)" alt="Flask">
&#x20; \<img src="[https://img.shields.io/badge/Cloud-AWS-FF9900?style=for-the-badge](https://img.shields.io/badge/Cloud-AWS-FF9900?style=for-the-badge)" alt="AWS">
\</p>

---

##  About the Project

**What if we could understand the risks of flooding, extreme heat, and water scarcity together instead of treating them as separate problems?**

Cities face increasingly interconnected environmental challenges. Heavy rainfall can cause flooding, prolonged dry periods can contribute to water shortages, and extreme heat can increase water demand when resources are already under pressure.

**AquaHeat AI** is a personal AI and machine-learning project designed to explore these connections through an interactive environmental intelligence platform.

It brings together environmental indicators, model-based risk assessment, scenario simulation, and potential resilience strategies in one place.

The goal is to help users explore environmental conditions, understand estimated risks, compare hypothetical scenarios, and investigate possible ways to improve heat and water resilience.

> **Too Much Water. Too Little Water. AI for the Balance in Between.**

##  Live Application

Experience AquaHeat AI here:

**🌐 Live Demo:** [https://aquaheat-ai.onrender.com/](https://aquaheat-ai.onrender.com/)

**💻 GitHub Repository:** [https://github.com/rohanbhowm25308/Aquaheat-AI](https://github.com/rohanbhowm25308/Aquaheat-AI)

Open the application to explore the dashboard, available location data, environmental risk indicators, and interactive simulation features.

---

## ✨ Key Features

###  1. Heat–Water Nexus Risk Intelligence

Explore the relationship between extreme heat and water-related environmental stress.

- Combined Heat–Water Nexus risk score.
- Separate heat, flood, and water-scarcity indicators.
- Environmental risk-factor analysis.
- Model-based estimates and uncertainty information.
- Scenario comparisons to explore changing environmental conditions.

The Nexus score is an experimental decision-support indicator, not an official government risk rating.

###  2. Smart Location Search

Explore environmental information for supported locations.

- Search for cities, districts, and localities.
- Retrieve available location and weather information.
- Update the dashboard based on the selected location.
- Explore location-related risk estimates.
- Handle unavailable data and incomplete geographic coverage.

Location search and environmental data availability depend on the configured providers. A weather result does not automatically represent verified local flood or groundwater conditions.

###  3. City Survival Twin

Explore a virtual environmental scenario for understanding urban climate and water stress.

- Examine heat and water-related indicators.
- Explore hypothetical environmental changes.
- Compare baseline and alternative scenarios.
- Investigate possible resilience measures.

The City Survival Twin is a simulation and decision-support concept, not a fully surveyed digital replica of a real city.

###  4. What-If Climate Simulator

Explore how environmental risk estimates respond when conditions change.

Experiment with variables such as:

- Temperature
- Rainfall
- Water demand
- Groundwater stress

Compare baseline and adjusted scenarios to investigate changes in estimated heat, flood, and water-scarcity risks.

Example scenarios include extreme heat, heavy rainfall, drought, and water conservation.

###  5. AI Environmental Decision Support

Explore environmental questions and possible responses through the AI assistance layer.

Example questions include:

- Why is the environmental risk score high?
- What measures could help during a heatwave?
- How can water consumption be reduced?
- What strategies could help prepare for water shortages?

Depending on the active configuration, the application can use an external AI provider or offline response templates.

AI-generated suggestions are intended to support exploration and should not replace expert advice or official emergency guidance.

###  6. AI Resilience Action Plans

Explore possible strategies for improving heat and water resilience.

Potential actions include:

- Water conservation and leak repair.
- Rainwater harvesting.
- Urban shade and green infrastructure.
- Heatwave preparedness.
- Water-resource planning.

The suggested measures depend on the available information and the scenario being explored.

###  7. Water Stress & Leak Intelligence

Investigate water-related challenges through available indicators and reporting features.

- Groundwater-stress indicators.
- Water-shortage reports.
- Community leak reports.
- Tanker-related reporting.
- Water-consumption anomaly checks where meter readings are supplied.

The reliability of these features depends on the data available. Demonstration reports and modelled values should not be confused with independently verified utility records.

###  8. Rainwater Harvesting & Flood-to-Resource Analysis

Explore the potential of using rainwater as a resource.

- Estimate potential rainwater collection.
- Investigate storage requirements.
- Explore water-budget scenarios.
- Compare hypothetical water-stress outcomes.
- Examine potential flood-mitigation measures.

Results are estimates based on supplied inputs and assumptions, not guaranteed real-world outcomes.

###  9. Environmental Alerts & Community Insights

Explore features designed to support environmental awareness.

- Environmental precautions and alerts.
- Community issue reporting.
- Water-shortage and leak reports.
- Environmental crisis summaries.
- Water-conservation insights.

Availability depends on the application's configuration and data sources. Browser notifications may require user permission.

###  10. Trust & Explainability Center

Transparency is an important part of environmental AI.

The platform's methodology section helps users understand:

- Environmental inputs and data sources.
- Risk-score calculations.
- Model uncertainty.
- Simulated versus observed information.
- Limitations of experimental predictions.

**The objective is not simply to produce a score, but to make its meaning and limitations easier to understand.**

---

##  How It Works

AquaHeat AI combines environmental information, machine-learning-based estimates, and interactive scenario analysis.

```text
User
  │
  ▼
AquaHeat AI Dashboard
  │
  ├── Location Search
  │      └── Geocoding and Available Weather Data
  │
  ├── Environmental Input Processing
  │
  ├── Machine-Learning Risk Assessment
  │      ├── Heat Risk
  │      ├── Flood-Risk Index
  │      ├── Water-Scarcity Risk
  │      └── Heat–Water Nexus Score
  │
  ├── What-If Climate Simulator
  │
  ├── AI Decision Support
  │
  └── Environmental Insights and Action Suggestions

Optional Cloud Infrastructure
  ├── Amazon S3
  ├── Amazon SageMaker
  └── Amazon Bedrock
```

Optional cloud services require their corresponding configuration, permissions, and deployed resources. The diagram describes the architecture and possible integrations, not a guarantee that every service is active in the live deployment.

---

##  Technology Stack

| Technology            | Purpose                                     |
| --------------------- | ------------------------------------------- |
| Python                | Application logic and model processing      |
| Flask                 | Backend web application                     |
| scikit-learn          | Machine-learning risk estimation            |
| NumPy                 | Numerical processing                        |
| HTML, CSS, JavaScript | Frontend interface and interactivity        |
| Open-Meteo            | Geocoding and available weather information |
| Amazon S3             | Optional environmental-data storage         |
| Amazon SageMaker      | Optional hosted ML inference                |
| Amazon Bedrock        | Optional AI-powered responses               |
| Groq                  | Optional AI provider                        |
| Gunicorn              | Production application server               |
| Render                | Live application hosting                    |

The exact active stack depends on the current application configuration.

---

##  Machine-Learning Approach

The prototype uses a **Gradient Boosting Regressor** and an ensemble of models to estimate environmental stress.

The model's simulated environmental inputs include:

- Temperature stress.
- Rainfall deficit.
- Water demand.
- Vegetation cover.
- Groundwater depletion.

The application also uses derived indicators and rule-based calculations to explore flood-related risk.

### Model Uncertainty

Agreement across ensemble models and input-uncertainty scenarios can be used to estimate model consistency.

This is not equivalent to a guarantee that a prediction is accurate.

### Important Model Limitation

The current prototype uses simulated training data, and its internal hold-out evaluation uses data generated by the same simulated process.

Therefore, its evaluation does not establish real-world forecasting accuracy.

Further development would require appropriate observed datasets, independent validation, geographic calibration, and testing against historical environmental events before the estimates could be relied upon for real-world decisions.

---

##  Environmental Data & Limitations

AquaHeat AI combines available environmental inputs with derived indicators and model-generated estimates.

| Information                    | Purpose                                                  |
| ------------------------------ | -------------------------------------------------------- |
| Temperature and rainfall       | Environmental inputs                                     |
| Weather forecasts              | Explore upcoming weather conditions where available      |
| Groundwater references         | Provide context where suitable reference data exists     |
| Water-demand indicators        | Explore potential water stress                           |
| Heat and water-scarcity scores | Model-generated risk estimates                           |
| Flood-risk index               | Estimate flood-related stress from configured indicators |
| Climate scenarios              | Compare hypothetical environmental changes               |

Data coverage varies by location. Some values may be simulated, estimated, or unavailable.

A modelled flood-risk index is not a flood warning, and a simulated climate scenario is not an official weather forecast.

For detailed methodology and data limitations, consult the application's **Methodology** section.

---

##  Run Locally

You can run AquaHeat AI on your own computer for development and experimentation.

### Prerequisites

- Python 3.10 or a compatible version.
- Git.
- Internet access for live environmental data.
- Optional API credentials for enabled external AI and AWS integrations.

### Step 1: Clone the Repository

```bash
git clone https://github.com/rohanbhowm25308/Aquaheat-AI.git
cd Aquaheat-AI
```

### Step 2: Create a Virtual Environment

**Windows**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Review `.env.example` and configure the variables required by the features you want to use.

For example:

```dotenv
LLM_PROVIDER=auto
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
USE_LIVE_DATA=0
S3_BUCKET=
SAGEMAKER_ENDPOINT=
AGENTCORE_RUNTIME_ARN=
GROQ_API_KEY=
OPEN_METEO_API_KEY=
```

These are illustrative settings. Use the region, provider, and model identifiers supported by your actual deployment. Not every variable is required.

**Security reminders:**

- Never commit `.env` files or secret keys.
- Do not place AWS credentials in frontend code.
- Use least-privilege IAM permissions.
- Verify third-party API usage policies and rate limits.

### Step 5: Start the Application

On Windows, if the repository's startup script is configured:

```bat
run.bat
```

Alternatively, try:

```bash
python app.py
```

Use the startup command specified by the current repository if it differs.

### Step 6: Open the Website

Navigate to:

**[http://127.0.0.1:5000](http://127.0.0.1:5000)**

Explore the dashboard and try a supported location or a demonstration scenario.

---

##  Optional AWS Integrations

The project includes optional paths for integrating cloud services.

- **Amazon S3:** Can store environmental data when configured.
- **Amazon SageMaker:** Can host model inference after a compatible model and endpoint have been deployed.
- **Amazon Bedrock:** Can power the AI decision-support layer when access and model permissions are configured.
- **Amazon Bedrock AgentCore:** Can support a separately configured agent runtime.

These services require their own deployment steps and permissions. Creating a cloud resource does not automatically connect it to the application.

---

- `app.py` — Flask application and core risk logic.
- `extras.py` — Additional feature modules.
- `geo.py` — Location search and environmental data handling.
- `static/` — Frontend assets.
- `aws/` — Optional AWS deployment resources.
- `agentcore/` — Optional agent-runtime configuration.
- `tests/` — Test files.
- `requirements.txt` — Python dependencies.

This is an overview; exact files and runtime-generated directories may vary with the repository version.

---

##  Explore These Scenarios

| Scenario               | What to investigate                                       |
| ---------------------- | --------------------------------------------------------- |
|  Heatwave            | How higher temperatures affect estimated heat risk        |
|  Heavy rainfall     | How rainfall changes affect the flood-risk index          |
|  Drought            | How reduced rainfall influences water-scarcity estimates  |
|  Water conservation  | How lower water demand changes the simulated outcome      |
|  Groundwater stress | How groundwater-stress inputs influence the Nexus score   |
|  Resilience planning | Which potential measures could be explored for a scenario |

These scenarios are intended for experimentation and learning, not as verified predictions of specific future events.

---

## 👨‍💻 About the Developer

**AquaHeat AI is an independent personal project developed by Rohan Bhowmik.**

The project explores how artificial intelligence, machine learning, environmental information, and interactive simulations can be combined to investigate heat and water resilience.

It is a learning and development project focused on making environmental challenges easier to explore and understand.

---

##  Feedback & Contributions

Suggestions, bug reports, and technical improvements are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Implement and test your changes.
4. Open a pull request describing your improvements.

Please avoid submitting credentials, private information, or unsupported environmental claims.

---

## 📜 License

A license has not been specified in this README. Check the repository for an existing license or add one if you want to establish permissions for others to use, modify, and redistribute the project.

---

\<p align="center">
&#x20; \<strong> AquaHeat AI\</strong>
&#x20; \<br>
&#x20; Predict Heat. Protect Water. Prevent Crisis.
&#x20; \<br>\<br>
&#x20; \<em>Too Much Water. Too Little Water. AI for the Balance in Between.\</em>
&#x20; \<br>\<br>
&#x20; \<a href="[https://aquaheat-ai.onrender.com/](https://aquaheat-ai.onrender.com/)">Explore the Live Application →\</a>
\</p>
