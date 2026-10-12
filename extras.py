"""Feature endpoints: City Twin, ranked action plans, community reports, alerts, water/leak intelligence, trust center."""
import json, threading, datetime
import numpy as np
from flask import jsonify, request

COST = {1: "Low (₹)", 2: "Medium (₹₹)", 3: "High (₹₹₹)"}
URG = ["Now (24-72 h)", "This week", "This month", "Plan this season"]
TYPES = {"leak": "Leak", "standing_water": "Standing water", "tanker": "Tanker request", "shortage": "Water shortage"}
# id, audience, title, relevant index, speed(0 fast..2 slow), cost tier, model effect, why, qualitative benefit, assumption
ACT = [
 ("save", "residents", "Cut non-essential water use by 10%", "scarcity", 0, 1, {"dem": -10}, "Water scarcity is {scarcity}/100 and groundwater stress is {gw}/100; every litre saved reduces pressure on a stressed supply.", "", "A 10% cut in discretionary use lowers demand growth by 10 points."),
 ("leaks_home", "residents", "Fix household leaks and dripping taps", "scarcity", 0, 1, {"dem": -4}, "Hidden leaks waste water exactly when supply is tight (scarcity {scarcity}/100).", "", "Assumes leaks account for about 4% of household demand (assumption)."),
 ("store", "residents", "Store 3 days of drinking water", "scarcity", 0, 1, {}, "Scarcity is {scarcity}/100; stored water protects your household if supply is interrupted.", "Preparedness: keeps drinking water available during a supply cut", "No model effect: a preparedness measure."),
 ("heat_safe", "residents", "Avoid outdoor work 12:00-16:00 and keep hydrated", "heat", 0, 1, {}, "Heat risk is {heat}/100; the hottest hours carry the greatest risk of heat illness.", "Health protection: lowers heat-illness risk for you and your family", "No model effect: a health precaution."),
 ("shade", "residents", "Add shade and cool roofing at home", "heat", 1, 2, {"t": -0.4}, "Heat risk is {heat}/100; shade and reflective roofs cool buildings and the street around them.", "", "Assumes shade and cool roofs lower the local heat anomaly by 0.4°C (assumption)."),
 ("harvest_home", "residents", "Install rooftop rainwater harvesting", "scarcity", 2, 2, {"def": -3, "dem": -6, "reduce": 0.10}, "Scarcity is {scarcity}/100 and flood risk is {flood}/100; captured roof water reduces both runoff and demand on the network.", "", "Assumes 30% of buildings adopt; lowers rainfall deficit 3 pts, demand 6 pts, runoff 10%."),
 ("report", "residents", "Report leaks and standing water on this platform", "scarcity", 0, 1, {}, "Community reports help authorities find losses and waterlogging faster.", "Faster repair of leaks and drainage faults", "No model effect: improves data for authorities."),
 ("tanker_prio", "authorities", "Prioritize tanker and supply to the highest-risk sectors", "scarcity", 0, 2, {"dem": -8}, "Scarcity is {scarcity}/100 with groundwater stress {gw}/100; targeted supply protects the most exposed neighbourhoods first.", "", "Assumes targeted supply offsets demand pressure by 8 points (assumption)."),
 ("cooling", "authorities", "Open cooling centres and hydration points", "heat", 0, 2, {}, "Heat risk is {heat}/100; public cooling spaces protect people without safe housing.", "Health protection for vulnerable groups during peak heat", "No model effect: a public-health measure."),
 ("drains", "authorities", "Clear and de-silt storm drains before heavy rain", "flood", 0, 2, {"drain": 0.15}, "Flood risk under a design storm is {flood}/100; blocked drains turn heavy rain into waterlogging.", "", "Assumes cleaning restores 15% of drainage capacity (assumption)."),
 ("leaks_net", "authorities", "Detect and repair leaks in the supply network", "scarcity", 1, 3, {"dem": -8}, "Scarcity is {scarcity}/100; reducing network losses is cheaper than finding new supply.", "", "Assumes recoverable losses equal 8 points of demand pressure (assumption)."),
 ("recharge", "authorities", "Build groundwater recharge pits and revive water bodies", "scarcity", 2, 3, {"gw": -6}, "Groundwater stress is {gw}/100 (CGWB-based); recharge is the only way to slow the long-term decline.", "", "Assumes one season of recharge lowers the groundwater stress index by 6 points (assumption)."),
 ("permeable", "authorities", "Add permeable pavements and bioswales in dense zones", "flood", 2, 3, {"imp": -0.06}, "Flood risk is {flood}/100; dense paved areas shed rain quickly and overload drains.", "", "Assumes 6 points less impervious cover (assumption)."),
 ("green", "authorities", "Plant trees and shade in heat-island zones", "heat", 1, 2, {"green": 6, "t": -0.3}, "Heat risk is {heat}/100; trees cool streets and reduce the urban heat-island effect.", "", "Assumes +6 points green cover and 0.3°C lower local heat anomaly (assumption)."),
 ("mandate", "authorities", "Require rainwater harvesting in new buildings", "scarcity", 2, 2, {"def": -3, "dem": -6, "reduce": 0.10}, "Scarcity is {scarcity}/100 and flood risk is {flood}/100; harvesting addresses both.", "", "Assumes 30% of buildings adopt harvesting."),
]
PREC = {"heat": ["Drink water regularly, even if not thirsty.", "Avoid outdoor activity from 12:00 to 16:00.", "Check on elderly neighbours, children and outdoor workers.", "Know your nearest cooling centre or shaded public space."],
        "scarcity": ["Store drinking water for 3 days.", "Postpone non-essential use (gardens, washing vehicles).", "Fix leaks and report them here.", "Keep tanker or supply contact numbers handy."],
        "flood": ["Keep drains and gutters near your home clear.", "Avoid low-lying roads and underpasses during heavy rain.", "Move valuables and electronics above ground level.", "Report standing water to the authorities."]}
SAMPLE = [("leak", "Sector 57", 5), ("leak", "Gurugram", 20), ("leak", "Delhi", 30), ("standing_water", "Gurugram", 3), ("standing_water", "Dwarka", 26),
          ("tanker", "Sector 57", 2), ("tanker", "Gurugram", 8), ("tanker", "Sohna", 15), ("shortage", "Faridabad", 6), ("shortage", "Manesar", 11), ("leak", "Noida", 40)]
SAMPLE_SERIES = [412, 405, 421, 398, 417, 409, 430, 402, 786, 415, 408, 419, 411, 792]

def init(m):
    app = m.app; LOCK = threading.Lock(); FILE = m.DATA_DIR / "reports.json"
    def load():
        try: return json.loads(FILE.read_text())
        except Exception: return []
    REPORTS = load()
    def clamp(d):
        try: v = [float(d.get(k, 0)) for k in ("temp", "rain", "cons", "gw")]
        except (TypeError, ValueError): v = [0, 0, 0, 0]
        return [float(x) for x in np.clip(v, [-5, -60, -40, -30], [6, 40, 60, 40])]
    def risk_with(n, eff, local=True):
        b = m.inputs(n); f = m.clipf([b[0] + eff.get("t", 0), b[1] + eff.get("def", 0), b[2] + eff.get("dem", 0), b[3] + eff.get("green", 0), b[4] + eff.get("gw", 0)])
        return m.risk(n, f, 0, local=local, reduce=eff.get("reduce", 0), drain=eff.get("drain", 0), imp=eff.get("imp", 0))

    # ---------- City Survival Twin ----------
    @app.route("/api/twin", methods=["POST"])
    def twin():
        j = request.get_json(silent=True) or {}; t, r, c, g = clamp(j); keys = ("nexus", "heat", "flood", "scarcity", "gw")
        req = j.get("locs"); names = []
        if isinstance(req, list):
            for n in req:
                if isinstance(n, str) and m.loc_ok(n) and n not in names: names.append(n)
            names = names[:8]
        if not names: names = list(m.LOCS)   # demo areas
        out = []
        for n in names:
            v = m.LOCS.get(n); b = m.inputs(n); base = m.SC[n]; f2 = m.clipf([b[0] + t, b[1] - r, b[2] + c, b[3], b[4] + g]); s = m.risk(n, f2, r, local=True)
            need = max(s["nexus"], s["heat"], s["flood"], s["scarcity"]); main = max(("heat", s["heat"]), ("flood", s["flood"]), ("scarcity", s["scarcity"]), key=lambda z: z[1])[0]
            out.append({"name": n, "x": v[0] if v else 50, "y": v[1] if v else 50, "density": m.imp_of(n), "geo": n in m.GEO, "base": {k: base[k] for k in keys}, "sim": {k: s[k] for k in keys},
                        "need": need, "base_need": max(base["nexus"], base["heat"], base["flood"], base["scarcity"]), "main": main, "why": [x["name"] for x in s["drivers"][:2]]})
        pri = sorted(out, key=lambda o: (-o["need"], -o["sim"]["nexus"]))
        return jsonify({"districts": out, "priority": [{"name": o["name"], "need": o["need"], "delta": o["need"] - o["base_need"], "main": o["main"], "why": o["why"]} for o in pri]})

    # ---------- AI Resilience Action Plan ----------
    _pc = {}
    def plan_for(n):
        key = (n, m.META["updated"], m.MODE["live"], m.live_on(), m.GEO[n]["ts"] if n in m.GEO else 0)
        if key in _pc: return _pc[key]
        _pc.clear(); cur = m.SC[n]; vals = {k: cur[k] for k in ("heat", "flood", "scarcity", "gw", "nexus", "demand")}; rows = []
        for aid, aud, title, rel, speed, cost, eff, why, qual, assum in ACT:
            rs = cur[rel]
            if rs < 35: continue
            urg = 0 if (rs >= 75 and speed == 0) else 1 if (rs >= 75 and speed == 1) or (rs >= 55 and speed == 0) else 2 if (rs >= 55 and speed <= 1) or (rs >= 35 and speed == 0) else 3
            ben = {}; 
            if eff:
                a = risk_with(n, eff)
                for lab, k in (("Nexus", "nexus"), ("Heat", "heat"), ("Flood", "flood"), ("Scarcity", "scarcity")):
                    d = cur[k] - a[k]
                    if d >= 1: ben[lab] = int(d)
            val = sum(ben.get(k, 0) * (1 if k == "Nexus" else .5) for k in ben) if eff else rs * .03
            text = ", ".join(f"-{v} {k}" for k, v in ben.items()) if ben else (qual or "Small modelled effect (under 1 point)")
            rows.append({"id": aid, "audience": aud, "title": title, "why": why.format(**vals), "urgency": URG[urg], "u": urg, "cost": COST[cost], "c": cost,
                         "benefit": text, "modelled": bool(ben), "value": round(val, 2), "assumption": assum})
        rows.sort(key=lambda z: (z["u"], -z["value"] / z["c"]))
        for aud in ("residents", "authorities"):
            for i, z in enumerate([z for z in rows if z["audience"] == aud], 1): z["rank"] = i
        _pc[key] = rows; return rows
    m.plan_for = plan_for
    @app.route("/api/actions")
    def actions():
        n = m.loc_of(request.args.get("loc"))[0]; rows = plan_for(n); cur = m.SC[n]
        return jsonify({"loc": n, "level": cur["level"], "nexus": cur["nexus"], "actions": rows,
                        "note": "Costs are indicative tiers, not quotes. Benefits are model-estimated score reductions under the stated assumptions."})

    # ---------- Community reports ----------
    def all_reports(loc=None):
        rows = [{"type": t, "loc": l, "note": "", "hours": h, "sample": True} for t, l, h in SAMPLE]
        now = datetime.datetime.now(datetime.timezone.utc)
        for r in REPORTS:
            try: hrs = (now - datetime.datetime.fromisoformat(r["ts"])).total_seconds() / 3600
            except Exception: hrs = 0
            rows.append({"type": r["type"], "loc": r["loc"], "note": r.get("note", ""), "hours": round(hrs, 1), "sample": False})
        rows = [z for z in rows if (not loc or z["loc"] == loc)]; rows.sort(key=lambda z: z["hours"]); return rows
    def counts(rows):
        c = {k: {"sample": 0, "community": 0} for k in TYPES}
        for z in rows: c[z["type"]]["sample" if z["sample"] else "community"] += 1
        return c
    @app.route("/api/reports", methods=["GET", "POST"])
    def reports():
        if request.method == "POST":
            d = request.json or {}; t = d.get("type"); l = d.get("loc"); note = str(d.get("note", ""))[:200].strip()
            if t not in TYPES or not m.loc_ok(l): return jsonify({"ok": False, "msg": "Choose a valid report type and location."}), 400
            with LOCK:
                REPORTS.append({"type": t, "loc": l, "note": note, "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}); del REPORTS[:-500]
                try: FILE.parent.mkdir(parents=True, exist_ok=True); FILE.write_text(json.dumps(REPORTS))
                except Exception: pass
        rows = all_reports(request.args.get("loc") if request.method == "GET" else None)
        pts = [{"loc": l, **{k: sum(1 for z in all_reports(l) if z["type"] == k) for k in TYPES}} for l in m.LOCS]
        return jsonify({"ok": True, "reports": rows[:40], "counts": counts(all_reports()), "by_loc": pts, "types": TYPES})

    # ---------- Alerts ----------
    @app.route("/api/alerts")
    def alerts():
        n = m.loc_of(request.args.get("loc"))[0]; s = m.SC[n]; rows = all_reports(n); out = []
        spec = (("heat", "Heatwave warning", s["heat"], s["heat_parts"], None), ("scarcity", "Water-shortage warning", s["scarcity"], s["scar_parts"], "shortage"), ("flood", "Flood and waterlogging alert", s["flood"], s["flood_parts"], "standing_water"))
        for k, title, sc, parts, rtype in spec:
            lv = m.level(sc)
            if lv == "LOW": continue
            if k == "flood": why = f"A {parts['Storm rainfall (mm/day)']} mm/day storm on {parts['Impervious cover (%)']}% paved ground would produce {parts['Runoff (mm)']} mm of runoff against {parts['Drainage capacity (mm/day)']} mm/day of drainage."
            else:
                top = max((p for p in parts.items() if p[0] != "Baseline"), key=lambda p: p[1]); why = f"Main factor: {top[0].lower()} (+{top[1]} points of {sc})."
            nrep = sum(1 for z in rows if z["type"] == rtype) if rtype else 0
            out.append({"type": k, "title": title if lv != "MODERATE" else title.replace("warning", "watch").replace("alert", "watch"), "level": lv, "score": sc, "why": why, "precautions": PREC[k],
                        "reports": nrep, "basis": "Model-based estimate, not an official warning.", "reports_note": (f"{nrep} unverified {TYPES[rtype].lower()} report(s) for {n}; verify with the local authority before acting" if rtype else "Heat risk has no community report type; use cooling-centre and hydration guidance.")})
        out.sort(key=lambda z: -z["score"])
        return jsonify({"loc": n, "alerts": out})

    # ---------- Water stress and leak intelligence ----------
    def cat(stage): return "Safe" if stage <= 70 else "Semi-critical" if stage <= 90 else "Critical" if stage <= 100 else "Over-exploited"
    @app.route("/api/water")
    def water():
        n = m.loc_of(request.args.get("loc"))[0]; st = m.GW_STAGE.get(n); rows = all_reports(n); allr = all_reports()
        if n in m.GEO:
            g = m.GEO[n]; gd = next((p for p in g["inputs_meta"] if p["name"].startswith("Groundwater stage")), None); st = (gd["value"], gd["source"]) if gd else None
        gw = {"index": round(m.inputs(n)[4]), "sourced": bool(st)}
        if st: gw.update(stage=st[0], category=cat(st[0]), source=st[1])
        else: gw.update(note="No reliable groundwater data is available for this location. The model assumed a neutral index of 30 and widened its uncertainty." if n in m.GEO else "No groundwater source loaded for this location; the index is an estimate.")
        if n in m.GURUGRAM_AREA: gw["trend"] = m.GW_REF["trend"]
        return jsonify({"loc": n, "groundwater": gw, "ref": {"facts": m.GW_REF["facts"], "sources": m.GW_REF["sources"], "method": m.GW_REF["method"]},
                        "counts": counts(rows), "city_counts": counts(allr), "sample_series": SAMPLE_SERIES})
    @app.route("/api/anomaly", methods=["POST"])
    def anomaly():
        try: s = [float(x) for x in (request.json or {}).get("series", [])]
        except (TypeError, ValueError): return jsonify({"ok": False, "msg": "Send numbers only."}), 400
        if len(s) < 7 or len(s) > 366: return jsonify({"ok": False, "msg": "Provide 7 to 366 daily readings."}), 400
        a = np.array(s); med = float(np.median(a)); mad = float(np.median(np.abs(a - med))) or max(1.0, .02 * med); z = .6745*(a - med)/mad
        flags = [{"day": i + 1, "value": float(v), "z": round(float(zz), 1), "flag": bool(abs(zz) > 3.5), "pct": round((float(v)/med - 1)*100)} for i, (v, zz) in enumerate(zip(a, z))]
        return jsonify({"ok": True, "median": round(med, 1), "mad": round(mad, 1), "threshold": 3.5, "days": flags, "flagged": sum(f["flag"] for f in flags)})

    # ---------- Trust and explainability ----------
    @app.route("/api/trust")
    def trust():
        n = m.loc_of(request.args.get("loc"))[0]
        if n in m.GEO:
            g = m.GEO[n]; s = m.SC[n]; tagmap = {"Observed": "live", "Forecast": "live", "Historical": "ref", "Model estimate": "proto", "Simulated": "sim", "Unavailable": "sim"}
            inp = [{"name": z["name"], "value": ("n/a" if z["value"] is None else z["value"]), "unit": z["unit"], "source": f'{z["type"]}: {z["source"]}', "tag": tagmap.get(z["type"], "proto"), "asof": z["time"] or "n/a"} for z in g["inputs_meta"]]
            real = sum(1 for z in inp if z["tag"] in ("live", "ref")); warn = list(g["warnings"]) + ["Flood risk is a rule-based index. No observed flood or waterlogging data is loaded.", "The Nexus model is trained on simulated data; hold-out scores prove consistency with the simulator, not real-world accuracy.", "Community reports are unverified."]
            return jsonify({"loc": n, "inputs": inp, "completeness": round(100*real/len(inp)), "real": real, "total": len(inp), "warnings": warn, "mode": "searched",
                "confidence": {"conf": s["conf"], "lo": s["lo"], "hi": s["hi"], "n": s["n"], "flood": [s["flood_lo"], s["flood_hi"]], "scarcity": [s["scar_lo"], s["scar_hi"]], "heat": [s["heat_lo"], s["heat_hi"]]},
                "drivers": s["drivers"], "model": {"algorithm": "Gradient Boosting Regressor", "holdout": m.HOLD, "features": len(m.FEATS)}})
        live = m.live_on(); s = m.SC[n]; b = m.inputs(n); inp = []; warn = []
        anch = live and (m.PROC.get(n) or {}).get("demand_growth") is not None; lv = live and n in m.PROC; st = m.GW_STAGE.get(n)
        when = f"Open-Meteo, updated {m.META['updated']}" if lv else "Simulated scenario (no observation time)"
        def add(name, val, unit, kind, tag, asof): inp.append({"name": name, "value": val, "unit": unit, "source": kind, "tag": tag, "asof": asof})
        add("Temperature anomaly", round(b[0], 1), "°C above normal", "Real (Open-Meteo)" if lv else "Simulated scenario", "live" if lv else "sim", when)
        add("Rainfall deficit", round(b[1], 1), "% below normal", "Real (Open-Meteo)" if lv else "Simulated scenario", "live" if lv else "sim", when)
        add("Water-demand growth", round(b[2], 1), "% above requirement", "Reported (GMDA/MCG via press)" if anch else "Modelled", "live" if anch else "proto", "Published figures, undated press reports" if anch else "Model assumption")
        add("Green cover", round(b[3]), "% vegetated", "Modelled" + (" + live soil-moisture proxy" if lv else ""), "proto", "Model assumption")
        add("Groundwater stress", round(b[4]), "index (stage ÷ 4)", f"Reported (CGWB 2024: {st[0]}%)" if st else "Estimated, no source loaded", "ref" if st else "proto", "CGWB 2024 assessment" if st else "Placeholder estimate")
        storm = m.storm_mm(n); add("Design storm", storm, "mm/day", "Real forecast (Open-Meteo)" if (lv and (m.PROC[n].get("storm_mm") is not None)) else "Simulated design storm", "live" if (lv and m.PROC[n].get("storm_mm") is not None) else "sim", when if lv else "Fixed design value")
        add("Imperviousness and drainage", round(m.imp_of(n)*100), "% paved (proxy)", "Modelled", "proto", "Model assumption, not surveyed")
        real = sum(1 for z in inp if z["tag"] in ("live", "ref")); comp = round(100*real/len(inp))
        if not lv: warn.append("Temperature, rainfall and the design storm are a simulated demo scenario. Switch to Live data for real weather inputs.")
        if live and not lv: warn.append(f"Live data is on but unavailable for {n}; demo inputs are being used.")
        if not st: warn.append(f"No groundwater source is loaded for {n}; its groundwater index is an estimate.")
        if not anch: warn.append("Water demand is modelled here (reported figures exist only for the Gurugram area in Live mode).")
        warn += ["Flood risk is a rule-based runoff-vs-drainage index. No observed flood or waterlogging data is loaded.", "The Nexus model is trained on simulated data; hold-out scores prove consistency with the simulator, not real-world accuracy."]
        sc = sum(1 for z in all_reports(n) if z["sample"]); 
        if sc: warn.append(f"{sc} leak, tanker or shortage reports shown for {n} are SAMPLE data until community reports arrive.")
        return jsonify({"loc": n, "inputs": inp, "completeness": comp, "real": real, "total": len(inp), "warnings": warn, "mode": "live" if live else "simulated",
            "confidence": {"conf": s["conf"], "lo": s["lo"], "hi": s["hi"], "n": s["n"], "flood": [s["flood_lo"], s["flood_hi"]], "scarcity": [s["scar_lo"], s["scar_hi"]], "heat": [s["heat_lo"], s["heat_hi"]]},
            "drivers": s["drivers"], "model": {"algorithm": "Gradient Boosting Regressor", "holdout": m.HOLD, "features": len(m.FEATS)}})
