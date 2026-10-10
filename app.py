import os, json, pathlib, threading, requests
import numpy as np
from flask import Flask, jsonify, request, render_template
from sklearn.ensemble import GradientBoostingRegressor
try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

# ---- Prototype ML model trained on SIMULATED environmental-stress data, designed to be replaced by live datasets
#      (IMD / CGWB / NASA POWER / Open-Meteo). Optional live weather inputs: set USE_LIVE_DATA=1.
# features: temp anomaly (°C), rainfall deficit (%), demand growth (%), green cover (%)
FEATS = ["Extreme Temperature", "Low Rainfall", "Water Demand", "Low Vegetation"]
BASE = np.array([0, 0, 0, 30.0])
rng = np.random.default_rng(7)
X = np.c_[rng.uniform(0, 6, 3000), rng.uniform(-20, 60, 3000), rng.uniform(-30, 50, 3000), rng.uniform(10, 60, 3000)]
y = np.clip(15 + 11*X[:,0] + .45*X[:,1] + .35*X[:,2] - .3*(X[:,3]-30), 0, 100) + rng.normal(0, 2, 3000)
model = GradientBoostingRegressor(random_state=7).fit(X, y)
# Ensemble of 12 models on bootstrap resamples: used for uncertainty / confidence (disagreement between members)
ENS = []
for k in range(12):
    ix = np.random.default_rng(100 + k).integers(0, len(X), 1500)
    ENS.append(GradientBoostingRegressor(n_estimators=60, max_depth=3, random_state=k).fit(X[ix], y[ix]))

SM_ENDPOINT = os.getenv("SAGEMAKER_ENDPOINT", "")
ENGINE = {"sm_ok": None, "client": None}
_h = GradientBoostingRegressor(random_state=7).fit(X[:2400], y[:2400]); _p = _h.predict(X[2400:])   # hold-out on the SAME simulated generator
HOLD = {"r2": round(float(1 - ((y[2400:]-_p)**2).sum()/((y[2400:]-y[2400:].mean())**2).sum()), 3), "mae": round(float(np.abs(y[2400:]-_p).mean()), 2)}

def nexus_value(f):
    """Nexus prediction: Amazon SageMaker real-time endpoint if configured, else the local model."""
    if SM_ENDPOINT:
        try:
            if ENGINE["client"] is None:
                import boto3
                from botocore.config import Config
                ENGINE["client"] = boto3.client("sagemaker-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"),
                                                config=Config(connect_timeout=3, read_timeout=6, retries={"max_attempts": 1}))
            r = ENGINE["client"].invoke_endpoint(EndpointName=SM_ENDPOINT, ContentType="application/json",
                                                 Body=json.dumps({"instances": [[float(v) for v in f]]}))
            v = float(json.loads(r["Body"].read())["predictions"][0]); ENGINE["sm_ok"] = True
            return float(np.clip(v, 0, 100))
        except Exception:
            ENGINE["sm_ok"] = False
    return float(np.clip(model.predict([np.array(f, float)])[0], 0, 100))

def level(s): return "LOW" if s < 35 else "MODERATE" if s < 55 else "HIGH" if s < 75 else "CRITICAL"

def score(f):
    f = np.array(f, float)
    nexus = nexus_value(f)
    drivers = []  # explainable AI: ablate each feature back to baseline
    for i, n in enumerate(FEATS):
        g = f.copy(); g[i] = BASE[i]
        drivers.append({"name": n, "value": round(nexus - float(model.predict([g])[0]))})
    drivers.sort(key=lambda d: -d["value"])
    heat = float(np.clip(35 + 14*f[0] + .1*(30-f[3]), 0, 100))
    water = float(np.clip(15 + .9*f[1] + .4*f[2], 0, 100))
    return {"nexus": round(nexus), "heat": round(heat), "water": round(water),
            "demand": round(float(np.clip(40 + 1.1*f[2] + 3*f[0], 0, 100))),
            "rain": round(float(np.clip(f[1] + 20, 0, 100))),
            "level": level(nexus), "drivers": drivers}

LOCS = {  # name: (map x%, y%, temp anomaly, rain deficit, demand growth, green cover)
    "Gurugram": (46, 62, 3.55, 41.5, 35, 40), "Sector 57": (52, 66, 3.9, 45, 40, 30),
    "Delhi": (58, 38, 3.6, 38, 33, 25), "Noida": (72, 48, 3.2, 35, 30, 35),
    "Faridabad": (64, 70, 3.0, 33, 28, 38), "Manesar": (34, 78, 2.2, 28, 22, 55),
    "Sohna": (52, 84, 2.0, 25, 20, 58), "Dwarka": (36, 44, 2.8, 32, 27, 40)}

@app.route("/")
def home(): return app.send_static_file("index.html")

@app.route("/api/locations")
def locations():
    return jsonify([{"name": n, "x": v[0], "y": v[1], "inputs": inputs(n), "rainfall": RAIN[n], **SC[n]} for n, v in LOCS.items()])

@app.route("/api/simulate", methods=["POST"])
def simulate():
    d = request.json; b = inputs(loc_of(d.get("loc"))[0])
    cur = score(b)
    sim_in = [b[0] + d["temp"], b[1] - d["rain"], b[2] + d["cons"], b[3]]; sim = score(sim_in); u = uncertainty(sim_in)   # d["rain"] = % CHANGE in rainfall (negative = drier = higher deficit)
    t, r, c = d["temp"], d["rain"], d["cons"]; delta = sim["nexus"] - cur["nexus"]
    parts = ([f"a +{t:g}°C temperature rise"] if t else []) + ([f"{abs(r):g}% {'less' if r < 0 else 'more'} rainfall"] if r else []) + ([f"{abs(c):g}% {'higher' if c > 0 else 'lower'} water consumption"] if c else [])
    what = (", ".join(parts[:-1]) + " and " + parts[-1] if len(parts) > 1 else parts[0]) if parts else None
    if not what: insight = "No change from the current scenario."
    elif delta > 0: insight = f"{what[0].upper()+what[1:]} could raise heat-water stress from {cur['nexus']} to {sim['nexus']} (+{delta}, {sim['level']}). Largest driver: {sim['drivers'][0]['name'].lower()}."
    elif delta < 0: insight = f"{what[0].upper()+what[1:]} could lower heat-water stress from {cur['nexus']} to {sim['nexus']} ({delta}, {sim['level']})."
    else: insight = f"{what[0].upper()+what[1:]} leaves heat-water stress at about {cur['nexus']}."
    mit = score([sim_in[0], sim_in[1], sim_in[2] - 20, sim_in[3]])["nexus"]
    mitigation = (f"Mitigation: cutting water consumption by a further 20% would bring the simulated risk from {sim['nexus']} to {mit}." if mit < sim["nexus"] else "Mitigation: water-use cuts alone would not lower this scenario; pair them with rainwater harvesting and cooling measures.")
    return jsonify({"current": cur["nexus"], "simulated": sim["nexus"], "level": sim["level"], "drivers": sim["drivers"], "conf": u["conf"], "lo": u["lo"], "hi": u["hi"], "insight": insight, "mitigation": mitigation})

def _bedrock(system, user):
    import boto3
    from botocore.config import Config
    c = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"),
                     config=Config(connect_timeout=5, read_timeout=20, retries={"max_attempts": 1}))
    r = c.converse(modelId=os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0"), system=[{"text": system}],
                   messages=[{"role": "user", "content": [{"text": user}]}], inferenceConfig={"maxTokens": 380, "temperature": .3})
    return r["output"]["message"]["content"][0]["text"]

def _groq(system, user):
    key = os.getenv("GROQ_API_KEY")
    if not key: return None
    r = requests.post("https://api.groq.com/openai/v1/chat/completions", timeout=15, headers={"Authorization": f"Bearer {key}"},
        json={"model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"), "temperature": .3, "max_tokens": 380,
              "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
    return r.json()["choices"][0]["message"]["content"]

def _agentcore(system, user):
    """Invoke an agent hosted on Amazon Bedrock AgentCore Runtime (see agentcore/agent.py)."""
    import boto3, uuid
    from botocore.config import Config
    c = boto3.client("bedrock-agentcore", region_name=os.getenv("AWS_REGION", "us-east-1"),
                     config=Config(connect_timeout=5, read_timeout=45, retries={"max_attempts": 1}))
    r = c.invoke_agent_runtime(agentRuntimeArn=os.environ["AGENTCORE_RUNTIME_ARN"], runtimeSessionId=uuid.uuid4().hex + uuid.uuid4().hex[:8],
                               payload=json.dumps({"prompt": system + "\n\n" + user}).encode())
    body = r["response"].read().decode()
    try:
        j = json.loads(body)
        return j["result"] if isinstance(j, dict) and "result" in j else (j if isinstance(j, str) else body)
    except ValueError:
        return body

def have_aws(): return bool(os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_PROFILE") or os.getenv("BEDROCK_ENABLED"))

def llm_name():
    p = os.getenv("LLM_PROVIDER", "auto").lower()
    if p in ("auto", "agentcore") and os.getenv("AGENTCORE_RUNTIME_ARN"): return "Amazon Bedrock AgentCore"
    if p in ("auto", "bedrock") and (p == "bedrock" or have_aws()): return "Amazon Bedrock"
    if p in ("auto", "groq") and os.getenv("GROQ_API_KEY"): return "Groq"
    return "Offline template"

def call_llm(system, user):
    """Amazon Bedrock first (if AWS configured), then Groq, else None -> offline template. Returns (text, provider)."""
    p = os.getenv("LLM_PROVIDER", "auto").lower()
    for name, fn, ok in (("Amazon Bedrock AgentCore", _agentcore, p in ("auto", "agentcore") and bool(os.getenv("AGENTCORE_RUNTIME_ARN"))),
                         ("Amazon Bedrock", _bedrock, p in ("auto", "bedrock") and (p == "bedrock" or have_aws())),
                         ("Groq", _groq, p in ("auto", "groq"))):
        if ok:
            try:
                t = fn(system, user)
                if t: return t, name
            except Exception:
                pass
    return None, "Offline template"

SYS = ("You are AquaHeat Intelligence, an environmental decision-support agent. Use ONLY the model output provided; never invent numbers. "
       'Reply with JSON only: {"assessment": "2-3 sentence risk assessment naming the top drivers", "actions": ["4 short, specific actions"]}. '
       "If the question names an audience (citizens, buildings, authorities) tailor the actions to it.")
DRV = {"Extreme Temperature": ("🔥", "Temperature anomaly"), "Low Rainfall": ("🌧️", "Rainfall deficit"), "Water Demand": ("💧", "Water demand"), "Low Vegetation": ("🌿", "Vegetation stress")}
qual = lambda v: "High" if v >= 20 else "Moderate" if v >= 8 else "Low"
ACTIONS = {"citizens": ["Reduce non-essential water use (gardens, car washing).", "Store drinking water for 72 hours.", "Avoid outdoor activity in the afternoon heat.", "Check on elderly neighbours and children."],
           "buildings": ["Optimize cooling schedules and set-points.", "Fix leaks and add greywater reuse.", "Install rainwater harvesting storage.", "Add shading and reflective roofing."],
           "authorities": ["Prioritize high-risk zones for water supply.", "Open and publicize cooling centres.", "Expand green cover in heat-island zones.", "Monitor reservoir and groundwater levels daily."],
           "general": ["Reduce non-essential water consumption.", "Increase water-storage preparedness.", "Prioritize cooling infrastructure.", "Monitor high-risk zones."]}

@app.route("/api/agent", methods=["POST"])
def agent():
    d = request.json or {}; name = d.get("loc", "Gurugram"); name = name if name in LOCS else "Gurugram"
    q = str(d.get("q") or "Why is the risk high?")[:300]; s = SC[name]
    drivers = [{"emoji": DRV[x["name"]][0], "label": DRV[x["name"]][1], "level": qual(x["value"]), "value": x["value"]} for x in s["drivers"]]
    ctx = json.dumps({"location": name, "nexus": s["nexus"], "level": s["level"], "confidence_pct": s["conf"], "likely_range": [s["lo"], s["hi"]],
                      "drivers": s["drivers"], "heat": s["heat"], "water_stress": s["water"], "demand": s["demand"],
                      "data_mode": "live weather inputs" if live_on() else "simulated demo scenario"})
    text, prov = call_llm(SYS, f"Model output: {ctx}\nQuestion: {q}"); out = None
    if text:
        try:
            out = json.loads(text[text.index("{"): text.rindex("}")+1])
            assert isinstance(out["assessment"], str) and isinstance(out["actions"], list) and out["actions"]
        except Exception:
            out = None
    if not out:
        prov = "Offline template"; ql = q.lower()
        aud = "citizens" if ("citizen" in ql or "household" in ql) else "buildings" if "building" in ql else "authorities" if ("authorit" in ql or "municip" in ql or "government" in ql) else "general"
        top = [x["name"].lower() for x in s["drivers"][:2]]
        out = {"assessment": f"{name}'s Nexus risk is {s['level'].lower()} ({s['nexus']}/100), driven mainly by {top[0]} and {top[1]}. Model confidence is {s['conf']}%.", "actions": ACTIONS[aud]}
    return jsonify({"assessment": out["assessment"], "actions": [str(x) for x in out["actions"]][:5], "drivers": drivers,
                    "level": s["level"], "nexus": s["nexus"], "conf": s["conf"], "provider": prov})


import datetime
RAIN = {"Gurugram": 550, "Sector 57": 550, "Delhi": 650, "Noida": 700, "Faridabad": 600, "Manesar": 520, "Sohna": 500, "Dwarka": 620}
DENS = {"Gurugram": .7, "Sector 57": .78, "Delhi": .9, "Noida": .72, "Faridabad": .65, "Manesar": .4, "Sohna": .3, "Dwarka": .75}
COORD = {"Gurugram": (28.46, 77.03), "Sector 57": (28.42, 77.10), "Delhi": (28.61, 77.21), "Noida": (28.57, 77.32),
         "Faridabad": (28.41, 77.31), "Manesar": (28.36, 76.94), "Sohna": (28.25, 77.07), "Dwarka": (28.59, 77.05)}
TMAX = [21, 24, 30, 37, 41, 40, 35, 34, 34, 33, 28, 23]          # approx. monthly normal max temp, Delhi NCR (deg C)
RAIN_M = [18, 17, 14, 9, 19, 55, 210, 247, 125, 13, 3, 8]        # approx. monthly normal rainfall, Delhi NCR (mm)
GURUGRAM_AREA = {"Gurugram", "Sector 57", "Manesar", "Sohna"}   # covered by GMDA / MCG supply figures
WATER_REF = {"area": "Gurugram (GMDA / Municipal Corporation Gurugram)", "kind": "Published figures reported in the press, not primary meter data",
    "figures": [{"label": "Water requirement (GMDA)", "mld": 640, "note": "Supplied by canals 570 MLD + tubewells 70 MLD"},
                {"label": "GMDA treated supply (2 plants)", "mld": 570, "note": "Chandu-Budhera 300 MLD + Basai 270 MLD"},
                {"label": "Peak-summer demand reported", "mld": 700, "note": "Reported to have touched 700 MLD against 570 MLD supplied"},
                {"label": "Municipal borewell capacity", "mld": 100, "note": "MCG runs about 600 borewells"},
                {"label": "Projected demand by 2026 (context only)", "mld": 970, "note": "Not used in the model"},
                {"label": "TERI projection for 2025 (context only)", "mld": 874.3, "note": "Mahindra-TERI assessment; not used in the model"}],
    "sources": [{"name": "The Tribune: Gurugram stares at water shortage", "url": "https://www.tribuneindia.com/news/haryana/gurugram-stares-at-water-shortage-508806/amp"},
                {"name": "The Tribune: Water crisis intensifies in parched Gurugram", "url": "https://www.tribuneindia.com/news/haryana/water-crisis-intensifies-in-parched-gurugram-623939"},
                {"name": "The Tribune: GMDA confident to fulfil locals' water demand", "url": "https://www.tribuneindia.com/news/haryana/despite-missed-deadlines-for-treatment-plants-gmda-confident-to-fulfil-locals-water-demand/amp"},
                {"name": "Mahindra-TERI Gurugram Water Sustainability Assessment (2021)", "url": "https://www.mahindra.com/press-release/tag/1847"}],
    "method": "Reported peak uplift = (700 - 640) / 640 = 9.4%. In Live mode the demand-growth input for Gurugram-area locations is this uplift scaled by how close the 7-day temperature outlook is to the hottest monthly normal (0 at the annual mean temperature, 1 at the peak). The scaling is a calibration to the reported figures, not a published elasticity; other NCR locations stay modelled."}

def demand_ref(tmax):
    gap = (700 - 640)/640*100; cool = sum(TMAX)/12; hot = max(TMAX)
    return round(float(np.clip(gap*np.clip((tmax - cool)/(hot - cool), 0, 1.5), 0, 20)), 1)

MODE = {"live": os.getenv("USE_LIVE_DATA", "0") == "1"}
PROC, META = {}, {"updated": None, "raw_ref": None, "proc_ref": None}
DATA_DIR = pathlib.Path(__file__).parent / "data"
S3_BUCKET = os.getenv("S3_BUCKET", "")
SD_SIM, SD_LIVE = np.array([.8, 8, 6, 5]), np.array([.5, 6, 6, 5])   # assumed input uncertainty (temp C, rain pts, demand pts, green pts)

def live_on(): return MODE["live"] and bool(PROC)

def inputs(n):
    b = list(LOCS[n][2:])
    if live_on() and n in PROC:
        p = PROC[n]; b[0], b[1] = p["anomaly"], p["deficit"]; b[3] = float(np.clip(b[3]*p["veg_idx"], 5, 70))
        if p.get("demand_growth") is not None: b[2] = p["demand_growth"]
    return b

def uncertainty(f):
    """Monte Carlo over input uncertainty x 12-model ensemble. Confidence = share of draws that keep the same risk level."""
    f = np.array(f, float); sd = SD_LIVE if live_on() else SD_SIM
    P = f + np.random.default_rng(1).normal(0, 1, (20, 4))*sd
    d = np.clip(np.concatenate([m.predict(P) for m in ENS]), 0, 100); bins = [35, 55, 75]
    c = int(np.digitize(model.predict([f])[0], bins))
    return {"conf": int(round(float((np.digitize(d, bins) == c).mean())*100)), "lo": int(round(np.percentile(d, 5))), "hi": int(round(np.percentile(d, 95))), "n": int(len(d))}

def rebuild():
    for n in LOCS:
        f = inputs(n); SC[n] = {**score(f), **uncertainty(f)}
SC = {}; rebuild()   # cached: instant responses

# ---- data layer: fetch -> S3 (or local mirror) -> process -> model
def _s3():
    import boto3
    return boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-east-1"))

def store(kind, payload):
    key = f"{kind}/{datetime.date.today()}/{datetime.datetime.now():%H%M}.json"; body = json.dumps(payload)
    if S3_BUCKET:
        try:
            _s3().put_object(Bucket=S3_BUCKET, Key=key, Body=body.encode(), ContentType="application/json")
            return f"s3://{S3_BUCKET}/{key}"
        except Exception:
            pass
    p = DATA_DIR / key; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(body)
    return f"local:data/{key}"

def load_latest():
    try:
        if S3_BUCKET:
            ks = sorted(o["Key"] for o in _s3().list_objects_v2(Bucket=S3_BUCKET, Prefix="processed/").get("Contents", []))
            if ks: return json.loads(_s3().get_object(Bucket=S3_BUCKET, Key=ks[-1])["Body"].read()), f"s3://{S3_BUCKET}/{ks[-1]}"
        fs = sorted((DATA_DIR / "processed").glob("*/*.json"))
        if fs: return json.loads(fs[-1].read_text()), f"local:data/processed/{fs[-1].parent.name}/{fs[-1].name}"
    except Exception:
        pass
    return None, None

def fetch_one(n):
    la, lo = COORD[n]
    r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=8, params={"latitude": la, "longitude": lo,
        "daily": "temperature_2m_max,precipitation_sum,et0_fao_evapotranspiration", "hourly": "soil_moisture_0_to_7cm",
        "past_days": 14, "forecast_days": 7, "timezone": "auto"})
    r.raise_for_status()
    return r.json()

def process(n, r):
    m = datetime.date.today().month - 1; d = r["daily"]
    nxt = [t for t in d["temperature_2m_max"][14:] if t is not None]; past = [p for p in d["precipitation_sum"][:14] if p is not None]
    sm = [s for s in r["hourly"]["soil_moisture_0_to_7cm"][:14*24] if s is not None]; et = [e for e in d["et0_fao_evapotranspiration"][:14] if e is not None]
    b = LOCS[n]; anomaly = float(np.clip(np.mean(nxt) - TMAX[m] + (b[2] - 3.0)*.35, 0, 6))
    deficit = float(np.clip((1 - sum(past)/max(RAIN_M[m]*14/30, 1))*100 + (b[3] - 38)*.35, -20, 60))
    return {"anomaly": round(anomaly, 2), "deficit": round(deficit, 1), "tmax_next7": round(float(np.mean(nxt)), 1), "rain_14d_mm": round(float(sum(past)), 1),
            "soil_moisture": round(float(np.mean(sm)), 3) if sm else None, "et0_mm_day": round(float(np.mean(et)), 2) if et else None,
            "veg_idx": round(float(np.clip(np.mean(sm)/0.25, .6, 1.2)), 2) if sm else 1.0,
            "demand_growth": demand_ref(float(np.mean(nxt))) if n in GURUGRAM_AREA else None}

def refresh_once():
    from concurrent.futures import ThreadPoolExecutor
    def job(n):
        try: return n, fetch_one(n)
        except Exception: return n, None
    with ThreadPoolExecutor(8) as ex: res = dict(ex.map(job, list(COORD)))
    raw, proc = {}, {}
    for n, r in res.items():
        if r:
            try: proc[n] = process(n, r); raw[n] = r
            except Exception: pass
    if proc:
        PROC.update(proc); now = datetime.datetime.now().isoformat(timespec="minutes")
        META.update(updated=now, raw_ref=store("raw", raw), proc_ref=store("processed", {"updated": now, "data": proc})); rebuild()

def refresh_loop():
    import time
    while True:
        try: refresh_once()
        except Exception: pass
        time.sleep(1800)

snap, ref = load_latest()
if snap: PROC.update(snap["data"]); META.update(updated=snap["updated"], proc_ref=ref); rebuild()

@app.route("/api/mode", methods=["POST"])
def mode():
    want = bool((request.json or {}).get("live"))
    if want and not PROC: refresh_once()
    if want and not PROC:
        return jsonify({"ok": False, "msg": "Live data unavailable (no connection)."}), 409
    MODE["live"] = want; rebuild()
    return jsonify({"ok": True, "live": want})

@app.route("/api/status")
def status():
    return jsonify({"source": "live" if live_on() else "simulated", "updated": META["updated"], "llm": llm_name()})

@app.route("/api/waterref")
def waterref(): return jsonify(WATER_REF)

@app.route("/api/model")
def model_info():
    live = live_on(); st = lambda real: "Real (Open-Meteo)" if live else "Simulated demo scenario"
    return jsonify({"algorithm": "Gradient Boosting Regressor (scikit-learn)", "output": "Nexus Risk Score, 0-100", "ensemble": len(ENS),
        "features": [{"name": "Temperature anomaly", "desc": "Degrees C above the seasonal baseline", "range": "0 to 6", "status": st(1)},
                     {"name": "Rainfall deficit", "desc": "% below normal rainfall", "range": "-20 to 60", "status": st(1)},
                     {"name": "Water-demand growth", "desc": "% by which demand exceeds the normal requirement", "range": "-30 to 50", "status": "Reported data (Gurugram area), modelled elsewhere" if live else "Estimated / modelled"},
                     {"name": "Green cover", "desc": "% vegetated area" + (" (adjusted by soil-moisture proxy)" if live else ""), "range": "10 to 60", "status": "Modelled estimate" + (" + live proxy" if live else "")}],
        "levels": {"LOW": "below 35", "MODERATE": "35 to 54", "HIGH": "55 to 74", "CRITICAL": "75 and above"},
        "training": {"samples": int(len(X)), "source": "Simulated environmental-stress data (rule-based generator plus noise)", "holdout": HOLD},
        "engine": "Amazon SageMaker real-time endpoint" if (SM_ENDPOINT and ENGINE["sm_ok"]) else "Local model in the Flask process",
        "llm": llm_name(), "mode": "live" if live else "simulated"})

@app.route("/methodology")
def methodology(): return app.send_static_file("methodology.html")

@app.route("/api/pipeline")
def pipeline():
    live = live_on(); ref = META["proc_ref"] or ""; llm = llm_name()
    headline = (f"Data: live weather inputs (Open-Meteo), updated {META['updated']}" if live else
                "Data: simulated demo scenario (peak heat-stress conditions)")
    anch = live and any((p or {}).get("demand_growth") is not None for p in PROC.values())
    src = [{"icon": "🌡", "label": "Temperature", "dataset": "Open-Meteo weather API (daily max, 7-day outlook vs monthly normal)",
            "status": "LIVE" if live else "SIMULATED", "tag": "live" if live else "sim", "note": "Anomaly vs approximate Delhi-NCR monthly normal." if live else "Demo scenario. Switch to Live data to use real weather."},
           {"icon": "🌧", "label": "Rainfall", "dataset": "Open-Meteo precipitation (last 14 days vs monthly normal)",
            "status": "LIVE" if live else "SIMULATED", "tag": "live" if live else "sim", "note": "Rainfall deficit = shortfall vs approximate monthly normal." if live else "Demo scenario."},
           {"icon": "🌿", "label": "Vegetation", "dataset": "Soil moisture + evapotranspiration (vegetation-stress proxy); green cover is a modelled estimate",
            "status": "LIVE PROXY" if live else "PROTOTYPE", "tag": "live" if live else "proto", "note": "Not NDVI. Satellite NDVI (e.g. Sentinel-2) is the planned upgrade."},
           {"icon": "💧", "label": "Water demand", "dataset": "Reported Gurugram supply and demand figures (GMDA / MCG, via press); modelled for other NCR locations",
            "status": "REPORTED DATA (GURUGRAM)" if anch else "PROTOTYPE", "tag": "live" if anch else "proto",
            "note": "Anchored to 640 MLD requirement vs 700 MLD reported peak. Not meter data; see Methodology for sources." if anch else "Modelled in demo mode. Reported Gurugram figures are used in Live mode (see Methodology)."}]
    s3 = "active" if ref.startswith("s3://") else "fallback" if ref else "idle"
    sm = "active" if (SM_ENDPOINT and ENGINE["sm_ok"]) else "fallback"
    stages = [{"name": "Environmental data", "state": "active" if live else "fallback", "detail": "Open-Meteo, 8 locations" if live else "Simulated demo scenario"},
              {"name": "Amazon S3", "state": s3, "detail": ref.split("/processed")[0] if s3 == "active" else ("Local mirror of S3 layout (set S3_BUCKET)" if ref else "No snapshot yet")},
              {"name": "Data processing", "state": "active" if PROC else "idle", "detail": "Anomaly, deficit, soil-moisture index" if PROC else "Waiting for live snapshot"},
              {"name": "Nexus engine", "state": "active", "detail": "Gradient boosting + 12-model ensemble"},
              {"name": "Amazon SageMaker AI", "state": sm, "detail": f"Endpoint: {SM_ENDPOINT}" if sm == "active" else ("Endpoint unreachable, using local model" if SM_ENDPOINT else "Not configured, using local model")},
              {"name": llm if llm.startswith("Amazon") else "Amazon Bedrock", "state": "active" if llm.startswith("Amazon") else "fallback", "detail": "Generative explanation layer" if llm.startswith("Amazon") else f"Fallback: {llm}"},
              {"name": "AquaHeat Agent", "state": "active", "detail": "Grounded in model output"},
              {"name": "Flask API + UI", "state": "active", "detail": "Dashboard and map"}]
    return jsonify({"live": live, "headline": headline, "sources": src, "stages": stages})

def loc_of(n):
    n = n if n in LOCS else "Gurugram"
    return n, LOCS[n]

@app.route("/api/forecast")
def forecast():
    n, v = loc_of(request.args.get("loc")); b = np.array(inputs(n), float); d = np.arange(31)
    F = np.c_[b[0] + .05*d + .4*np.sin(d/2.5), b[1] + .25*d, b[2] + .3*d + 2*np.sin(d/4), np.full(31, b[3])]
    nx = np.clip(model.predict(F), 0, 100)
    heat = np.clip(35 + 14*F[:, 0] + .1*(30-F[:, 3]), 0, 100); water = np.clip(15 + .9*F[:, 1] + .4*F[:, 2], 0, 100)
    return jsonify({"nexus": nx.round().tolist(), "heat": heat.round().tolist(), "water": water.round().tolist()})

BUD = {"Household": (1, [.31, .14, .28, .27]), "Apartment": (2.6, [.38, .18, .10, .34]), "School": (9, [.45, .12, .18, .25]),
       "Office": (6, [.40, .20, .08, .32]), "Community": (30, [.30, .12, .35, .23])}
PARTS = ["Bathroom", "Kitchen", "Gardening", "Other"]
TIPS = {"Bathroom": "fit low-flow taps and shorten showers", "Kitchen": "run full dishwasher loads and fix drips",
        "Gardening": "water at dawn and mulch beds", "Other": "reuse greywater for cleaning"}

@app.route("/api/budget", methods=["POST"])
def budget():
    d = request.json or {}; m, sh = BUD.get(d.get("type"), BUD["Household"]); n, v = loc_of(d.get("loc"))
    rec = int(round(420*m)); est = int(round(510*m*(1 + (SC[n]["nexus"]-60)/400))); save = max(0, est-rec)
    parts = [{"name": p, "litres": int(round(est*s))} for p, s in zip(PARTS, sh)]
    top = max(parts, key=lambda x: x["litres"])["name"]
    return jsonify({"rec": rec, "est": est, "save": save, "parts": parts,
        "plan": f"Save approximately {int(save*.85)}-{save} L/day. Start with {top.lower()}: {TIPS[top]}."})

COEF = {"House": .8, "Apartment": .75, "School": .85, "Office": .7, "Factory": .9}
DEM = {"House": 1, "Apartment": 2.6, "School": 9, "Office": 6, "Factory": 20}

@app.route("/api/harvest", methods=["POST"])
def harvest():
    d = request.json or {}; n, v = loc_of(d.get("loc")); bt = d.get("btype") if d.get("btype") in COEF else "House"
    try:
        roof = float(np.clip(float(d.get("roof", 120)), 10, 20000)); rain = float(np.clip(float(d.get("rain", RAIN[n])), 100, 3000))
    except (TypeError, ValueError):
        roof, rain = 120.0, float(RAIN[n])
    cap = int(round(roof*rain*COEF[bt])); store = max(500, int(np.ceil(cap/365*30/500))*500)
    cover = min(1.0, cap/(510*365*DEM[bt])); f = inputs(n); g = [f[0], f[1]-cover*30, f[2]-cover*60, f[3]]
    a, b = score(f), score(g)
    return jsonify({"capture": cap, "storage": store, "cover": round(cover*100), "before": {"nexus": a["nexus"], "level": a["level"]},
        "after": {"nexus": b["nexus"], "level": b["level"]},
        "rec": f"Install a {store:,} L tank (about 30 days of stored supply). It can offset {round(cover*100)}% of this {bt.lower()}'s annual demand."})

@app.route("/api/heatisland")
def heat_island():
    n, v = loc_of(request.args.get("loc")); r = np.random.default_rng(sum(map(ord, n)))
    R, C = 9, 14; yy, xx = np.mgrid[0:R, 0:C]; cx, cy = r.uniform(3, 10), r.uniform(2, 6)
    dens = np.clip(DENS[n]*np.exp(-(((xx-cx)/5)**2 + ((yy-cy)/3)**2)) + .15 + r.normal(0, .05, (R, C)), 0, 1)
    veg = np.clip(v[5]/100*1.5*(1-dens*.8) + r.normal(0, .04, (R, C)), 0, 1)
    t = 33 + inputs(n)[0]*1.1 + 5*dens - 4*veg + r.normal(0, .3, (R, C))
    z = np.where((t > np.percentile(t, 70)) & (veg < .3) & (dens > .5), "heat", np.where(veg > .45, "green", np.where(dens > .55, "dense", "mixed")))
    share = float((z == "heat").mean())
    risk = int(np.clip(25 + inputs(n)[0]*8 + 20*dens.mean() - 20*veg.mean() + 120*share, 0, 100))
    return jsonify({"cells": [[{"z": str(z[i, j]), "t": round(float(t[i, j]), 1)} for j in range(C)] for i in range(R)],
        "risk": risk, "level": level(risk), "share": round(share*100),
        "factors": {"temp": round(float(t.mean()), 1), "veg": round(float(veg.mean())*100), "dens": round(float(dens.mean())*100),
                    "surface": round(float(np.clip(dens.mean()*85+10, 0, 100)))}})

CH = {"water": {"unit": "L saved", "d": {"Sector A": 18420, "Sector B": 14820, "Sector C": 11250, "Sector D": 8900, "Sector E": 6100}},
      "heat": {"unit": "pts", "d": {"Sector A": 940, "Sector B": 1210, "Sector C": 780, "Sector D": 1105, "Sector E": 620}}}

@app.route("/api/challenge", methods=["GET", "POST"])
def challenge():
    if request.method == "POST":
        try:
            d = request.json; c = CH.get(d.get("challenge")); s = d.get("sector")
            if c and s in c["d"]: c["d"][s] += max(0, min(5000, int(d.get("amount", 0))))
        except (TypeError, ValueError):
            pass
    return jsonify({k: {"unit": c["unit"], "board": sorted(([n, a] for n, a in c["d"].items()), key=lambda x: -x[1])} for k, c in CH.items()})

@app.route("/api/brief", methods=["POST"])
def brief():
    n, v = loc_of((request.json or {}).get("loc")); s = SC[n]; month = datetime.datetime.now().strftime("%B %Y")
    text, prov = call_llm("You are AquaHeat Intelligence. Write a concise environmental crisis brief (max 200 words) using ONLY the data given. "
                     "Sections: one-paragraph summary, Top 3 concerns, Recommended interventions.", json.dumps({"location": n, "month": month, **s}))
    if not text:
        prov = "Offline template"
        top = [x["name"] for x in s["drivers"][:3]]
        text = (f"{n} Environmental Brief - {month}\n\nThe region is in a {s['level'].lower()} heat-water stress period (Nexus {s['nexus']}/100). "
                f"{top[0]} and {top[1].lower()} are the primary risk factors.\n\nTop 3 concerns\n- {top[0]}\n- {top[1]}\n- {top[2]}\n\n"
                "Recommended interventions\n- Prioritize high-risk zones\n- Promote water conservation\n- Increase cooling infrastructure\n- Monitor water availability")
    return jsonify({"brief": text, "provider": prov})

_bg = {"on": False}
def start_background():
    """Start the 30-minute live-data refresh once (works under both `python app.py` and gunicorn)."""
    if not _bg["on"]:
        _bg["on"] = True; threading.Thread(target=refresh_loop, daemon=True).start()

start_background()

if __name__ == "__main__":
    print("AquaHeat AI running at http://127.0.0.1:5000  (open this in your browser)")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
