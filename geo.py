"""Smart location search and hyperlocal climate intelligence.
Providers (no API key needed): Open-Meteo Geocoding, Forecast, Archive (10-year normals) and Flood APIs; Nominatim for reverse labels.
Optional OPEN_METEO_API_KEY (server-side only) is added to Open-Meteo requests when set."""
import os, math, time, threading, datetime
from collections import OrderedDict
import numpy as np, requests
from flask import jsonify, request

UA = {"User-Agent": "AquaHeatAI/1.0 (hackathon prototype)"}
URL = {"geo": "https://geocoding-api.open-meteo.com/v1/search", "fc": "https://api.open-meteo.com/v1/forecast", "arch": "https://archive-api.open-meteo.com/v1/archive",
       "flood": "https://flood-api.open-meteo.com/v1/flood", "rev": "https://nominatim.openstreetmap.org/reverse"}
TTL = {"geo": 3600, "fc": 900, "clim": 86400, "flood": 3600, "rev": 86400}
GW_POINTS = [("Gurugram", 28.46, 77.03, 18), ("Manesar", 28.36, 76.94, 12), ("Sohna", 28.25, 77.07, 12), ("Faridabad", 28.41, 77.31, 15)]  # CGWB-sourced areas (name, lat, lon, radius km)
SOUTH_ASIA = {"IN", "PK", "BD", "NP", "LK", "BT", "MM"}
_CACHE, _CL, _RL = {}, threading.Lock(), {}
EVICT_AT = 40

class ProviderError(Exception):
    def __init__(self, kind, msg, status=502): super().__init__(msg); self.kind, self.msg, self.status = kind, msg, status

def cget(k):
    with _CL:
        v = _CACHE.get(k)
        if v and v[0] > time.time(): return v[1]
        _CACHE.pop(k, None)
def cset(k, val, ttl):
    with _CL:
        if len(_CACHE) > 300:
            for kk in [kk for kk, vv in _CACHE.items() if vv[0] < time.time()] or list(_CACHE)[:60]: _CACHE.pop(kk, None)
        _CACHE[k] = (time.time() + ttl, val)

def http_json(url, params, timeout=8, headers=UA):
    key = os.getenv("OPEN_METEO_API_KEY")
    if key and "open-meteo.com" in url: params = {**params, "apikey": key}
    try: r = requests.get(url, params=params, timeout=timeout, headers=headers)
    except requests.Timeout: raise ProviderError("timeout", "The data provider took too long to respond.", 504)
    except requests.RequestException: raise ProviderError("network", "The data provider could not be reached.", 503)
    if r.status_code == 429: raise ProviderError("rate_limited", "The data provider is rate limiting requests. Please wait a minute and try again.", 429)
    try: j = r.json()
    except ValueError: raise ProviderError("bad_response", "The data provider returned an unreadable response.", 502)
    if r.status_code >= 500: raise ProviderError("provider_error", "The data provider reported an internal error.", 502)
    if r.status_code >= 400 or (isinstance(j, dict) and j.get("error")): raise ProviderError("rejected", str((j or {}).get("reason", "Request rejected")) if isinstance(j, dict) else "Request rejected", r.status_code)
    return j

def hav(a, b, c, d):
    p = math.pi/180; x = math.sin((c-a)*p/2)**2 + math.cos(a*p)*math.cos(c*p)*math.sin((d-b)*p/2)**2
    return 12742*math.asin(math.sqrt(x))
def fin(x):
    try: return x is not None and math.isfinite(float(x))
    except (TypeError, ValueError): return False
def clean(a): return [float(x) for x in (a or []) if fin(x)]
def mean(a): a = list(a); return sum(a)/len(a) if a else None
def make_label(p):
    parts = [p.get("name")]
    for x in (p.get("admin1"), p.get("country")):
        if x and x not in parts: parts.append(x)
    return ", ".join(x for x in parts if x)
def parse_coord(lat, lon):
    try: la, lo = float(lat), float(lon)
    except (TypeError, ValueError): return None
    return (la, lo) if math.isfinite(la) and math.isfinite(lo) and -90 <= la <= 90 and -180 <= lo <= 180 else None

def init(m):
    app = m.app; GEO = m.GEO; LOCK = threading.Lock()
    def ip(): return (request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr or "?")
    def limited(bucket, limit, window):
        now = time.time(); q = _RL.setdefault((ip(), bucket), []); q[:] = [t for t in q if now - t < window]
        if len(q) >= limit: return True
        q.append(now); return False
    def err(kind, msg, status): return jsonify({"error": kind, "message": msg}), status

    # ---------- geocoding ----------
    def place(r):
        return {"id": r.get("id"), "name": r.get("name"), "admin1": r.get("admin1"), "admin2": r.get("admin2"), "country": r.get("country"), "country_code": r.get("country_code"),
                "lat": float(r["latitude"]), "lon": float(r["longitude"]), "elevation": r.get("elevation"), "population": r.get("population"), "timezone": r.get("timezone"),
                "feature": r.get("feature_code"), "label": make_label(r)}
    def builtin(q):
        out = []
        for n, v in m.LOCS.items():
            if q.lower() in n.lower():
                la, lo = m.COORD[n]; out.append({"id": None, "name": n, "admin1": "Delhi NCR", "admin2": None, "country": "India", "country_code": "IN", "lat": la, "lon": lo, "elevation": None, "population": None, "timezone": "Asia/Kolkata", "feature": "BUILTIN", "label": n + ", Delhi NCR, India"})
        return out
    @app.route("/api/map-config")
    def map_config():
        """Map tile source. Default: OpenStreetMap standard tiles (no API key), darkened in CSS to match the theme.
        Override with MAP_TILE_URL / MAP_TILE_ATTRIBUTION / MAP_TILE_DARKEN=0|1. A tile key, if any, is necessarily visible to browsers, so use a domain-restricted key."""
        url = os.getenv("MAP_TILE_URL") or "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        return jsonify({"url": url, "attribution": os.getenv("MAP_TILE_ATTRIBUTION") or "© OpenStreetMap contributors",
                        "darken": (os.getenv("MAP_TILE_DARKEN", "1") != "0") if not os.getenv("MAP_TILE_URL") else os.getenv("MAP_TILE_DARKEN", "0") == "1", "max_zoom": 19})

    @app.route("/api/locations/search")
    def search():
        q = " ".join((request.args.get("q") or "").split())
        if len(q) < 2 or len(q) > 80: return err("bad_query", "Type at least 2 characters (up to 80) to search.", 400)
        if limited("search", 40, 60): return err("rate_limited", "Too many searches. Please wait a few seconds.", 429)
        try: count = max(1, min(10, int(request.args.get("count", 8))))
        except ValueError: count = 8
        k = ("geo", q.lower(), count); res = cget(k)
        if res is None:
            try:
                j = http_json(URL["geo"], {"name": q, "count": count, "language": "en", "format": "json"}, timeout=6)
                res = [place(r) for r in (j.get("results") or []) if fin(r.get("latitude")) and fin(r.get("longitude"))]
                seen = {}
                for p in res:   # disambiguate duplicate labels
                    seen[p["label"]] = seen.get(p["label"], 0) + 1
                for p in res:
                    if seen[p["label"]] > 1: p["label"] += f" ({p['admin2']})" if p.get("admin2") and p["admin2"] not in p["label"] else f" ({p['lat']:.2f}, {p['lon']:.2f})"
                cset(k, res, TTL["geo"])
            except ProviderError as e:
                b = builtin(q)
                if b: return jsonify({"results": b, "degraded": True, "message": "The geocoding service is unavailable, so only built-in Delhi NCR areas are shown."})
                return err("geocoder_unavailable", e.msg + " Please try again shortly.", e.status if e.status in (429, 503, 504) else 503)
        return jsonify({"results": res, "degraded": False, "message": "" if res else f"No place found for “{q}”. Check the spelling or try a nearby city."})

    # ---------- environmental data ----------
    def forecast(lat, lon, refresh):
        k = ("fc", round(lat, 2), round(lon, 2))
        if not refresh and cget(k): return cget(k)
        j = http_json(URL["fc"], {"latitude": lat, "longitude": lon, "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,et0_fao_evapotranspiration", "hourly": "soil_moisture_0_to_7cm",
            "past_days": 14, "forecast_days": 7, "timezone": "auto"}, timeout=10)
        d = j.get("daily") or {}
        if len(d.get("time", [])) < 21 or len(clean(d.get("temperature_2m_max", [])[14:])) < 3: raise ProviderError("incomplete", "The forecast for this location is incomplete.", 502)
        cset(k, j, TTL["fc"]); return j
    def climatology(lat, lon):
        today = datetime.datetime.now(datetime.timezone.utc).date(); k = ("clim", round(lat, 1), round(lon, 1), today)
        if cget(k): return cget(k)
        y1 = today.year - 1; y0 = y1 - 9
        j = http_json(URL["arch"], {"latitude": lat, "longitude": lon, "start_date": f"{y0}-01-01", "end_date": f"{y1}-12-31", "daily": "temperature_2m_max,precipitation_sum", "timezone": "auto"}, timeout=20)
        d = j.get("daily") or {}; T, P = {}, {}
        for t, x, p in zip(d.get("time", []), d.get("temperature_2m_max", []), d.get("precipitation_sum", [])):
            dt = datetime.date.fromisoformat(t)
            if fin(x): T[dt] = float(x)
            if fin(p): P[dt] = float(p)
        tw, rs = [], []
        for y in range(y0, y1 + 1):
            c = datetime.date(y, today.month, min(today.day, 28)); days = [c + datetime.timedelta(i) for i in range(-15, 16)]
            tv = [T[x] for x in days if x in T]; pv = [P[x] for x in days if x in P]
            if len(tv) >= 25 and len(pv) >= 25: tw += tv; rs.append(sum(pv)*31/len(pv))
        ann = [sum(v for dd, v in P.items() if dd.year == y) for y in range(y0, y1 + 1) if sum(1 for dd in P if dd.year == y) >= 330]
        if len(rs) < 5 or len(tw) < 100: raise ProviderError("incomplete", "Climate normals for this location are incomplete.", 502)
        out = {"tmax_norm": mean(tw), "rain31_norm": mean(rs), "annual_rain": mean(ann), "years": len(rs), "period": f"{y0}-{y1}"}
        cset(k, out, TTL["clim"]); return out
    def flood(lat, lon):
        k = ("flood", round(lat, 2), round(lon, 2))
        if cget(k) is not None: return cget(k)
        try: j = http_json(URL["flood"], {"latitude": lat, "longitude": lon, "daily": "river_discharge", "past_days": 7, "forecast_days": 7}, timeout=8)
        except ProviderError as e:
            if e.kind in ("rejected",): j = {"daily": {}}
            else: raise
        cset(k, j, TTL["flood"]); return j
    def bundle(lat, lon, refresh=False):
        out = {}
        def job(n, fn, *a):
            try: out[n] = fn(*a)
            except ProviderError as e: out[n] = e
            except Exception: out[n] = ProviderError("internal", "Unexpected error while reading provider data.", 502)
        ts = [threading.Thread(target=job, args=("fc", forecast, lat, lon, refresh)), threading.Thread(target=job, args=("clim", climatology, lat, lon)), threading.Thread(target=job, args=("flood", flood, lat, lon))]
        [t.start() for t in ts]; [t.join(25) for t in ts]
        for k in ("fc", "clim", "flood"): out.setdefault(k, ProviderError("timeout", "The data provider took too long to respond.", 504))
        return out
    def reverse(lat, lon):
        k = ("rev", round(lat, 2), round(lon, 2))
        if cget(k): return cget(k)
        try:
            j = http_json(URL["rev"], {"format": "jsonv2", "lat": lat, "lon": lon, "zoom": 10, "accept-language": "en"}, timeout=5); a = j.get("address") or {}
            nm = a.get("city") or a.get("town") or a.get("village") or a.get("suburb") or a.get("county") or a.get("state_district")
            p = {"name": nm, "admin1": a.get("state"), "country": a.get("country"), "country_code": (a.get("country_code") or "").upper() or None}
            if nm: lab = make_label(p); cset(k, (p, lab), TTL["rev"]); return p, lab
        except ProviderError: pass
        return {"name": None, "admin1": None, "country": None, "country_code": None}, f"Your location ({lat:.3f}, {lon:.3f})"
    def gw_near(lat, lon):
        best = None
        for n, la, lo, r in GW_POINTS:
            dkm = hav(lat, lon, la, lo)
            if dkm <= r and (best is None or dkm < best[1]): best = (n, dkm)
        if not best: return None
        st = m.GW_STAGE[best[0]]; return {"area": best[0], "stage": st[0], "source": st[1], "dist_km": round(best[1], 1)}
    def imp_pop(pop): return None if not pop else .25 if pop < 5e4 else .40 if pop < 5e5 else .60 if pop < 5e6 else .75

    def derive(lat, lon, pl, b):
        """Turn provider data into display data, provenance and model inputs. Raises ProviderError if the model inputs cannot be derived."""
        fc, cl, fl = b["fc"], b["clim"], b["flood"]
        if isinstance(fc, ProviderError): raise fc
        d = fc["daily"]; cur = fc.get("current") or {}; cu = fc.get("current_units") or {}; ft = fc.get("fetched_note")
        t_next = clean(d["temperature_2m_max"][14:]); p_past = clean(d["precipitation_sum"][:14]); p_next = clean(d["precipitation_sum"][14:])
        e_past = clean(d.get("et0_fao_evapotranspiration", [])[:14]); e_next = clean(d.get("et0_fao_evapotranspiration", [])[14:]); pr_next = clean(d.get("precipitation_probability_max", [])[14:])
        sm = clean((fc.get("hourly") or {}).get("soil_moisture_0_to_7cm", [])[:14*24]); now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes")
        clim_ok = not isinstance(cl, ProviderError); flood_ok = not isinstance(fl, ProviderError) and bool(clean((fl.get("daily") or {}).get("river_discharge", [])))
        country = pl.get("country_code"); gwi = gw_near(lat, lon); prov, lim, warn, val = [], [], [], []
        def row(name, value, unit, typ, source, when, note=""): prov.append({"name": name, "value": value, "unit": unit, "type": typ, "source": source, "time": when, "note": note})
        S_FC, S_CL, S_FL = "Open-Meteo forecast API (weather-model analysis and forecast)", "Open-Meteo archive API (ERA5-based reanalysis)", "Open-Meteo Flood API (GloFAS river-discharge model)"
        ctime = cur.get("time"); data = {"fetched_at": now, "data_time": ctime, "timezone": fc.get("timezone"), "elevation": fc.get("elevation")}
        if cur: data["current"] = {"temp": cur.get("temperature_2m"), "feels": cur.get("apparent_temperature"), "humidity": cur.get("relative_humidity_2m"), "wind": cur.get("wind_speed_10m"), "precip": cur.get("precipitation"), "units": cu}
        if cur.get("temperature_2m") is not None: row("Current temperature", cur["temperature_2m"], cu.get("temperature_2m", "°C"), "Observed", S_FC, ctime, "Model analysis for the grid cell, not a station reading")
        row("Forecast max temperature (next 7 days)", round(max(t_next), 1), "°C", "Forecast", S_FC, ctime)
        if clim_ok:
            norm = cl["tmax_norm"]; anom_raw = mean(t_next) - norm; hot = sum(1 for x in t_next if x >= norm + 4)
            row("Normal max temperature (this time of year)", round(norm, 1), "°C", "Historical", S_CL, cl["period"], f"Mean of {cl['years']} years, ±15-day window")
            row("Heat anomaly (7-day mean max vs normal)", round(anom_raw, 1), "°C", "Model estimate", S_FC + " + " + S_CL, ctime)
            spell = "Heat spell likely" if hot >= 3 else "Some hot days ahead" if hot >= 1 else "No unusual heat in the forecast"
            imd = bool(country == "IN" and max(t_next) >= 40 and max(t_next) - norm >= 4.5)
            data["heat"] = {"max7": round(max(t_next), 1), "mean7": round(mean(t_next), 1), "normal": round(norm, 1), "anomaly": round(anom_raw, 1), "hot_days": hot, "spell": spell, "imd_like": imd,
                            "note": "Indicator only, not an official warning. Hot day = forecast max at least 4°C above normal." + (" Forecast meets IMD-style heatwave thresholds (40°C and 4.5°C above normal)." if imd else "")}
            n14 = cl["rain31_norm"]*14/31; defr = (1 - sum(p_past)/n14)*100 if n14 >= 3 else None
            row("Rainfall, last 14 days", round(sum(p_past), 1), "mm", "Observed", S_FC, ctime, "Model-analysed precipitation")
            row("Normal rainfall for 14 days", round(n14, 1), "mm", "Historical", S_CL, cl["period"])
            data["rain"] = {"past14": round(sum(p_past), 1), "normal14": round(n14, 1), "deficit_pct": None if defr is None else round(defr), "next7": round(sum(p_next), 1), "max_day": round(max(p_next), 1) if p_next else None, "prob_max": max(pr_next) if pr_next else None,
                            "monsoon_window": bool(country in SOUTH_ASIA and 6 <= datetime.date.today().month <= 9), "annual_normal": round(cl["annual_rain"]) if cl.get("annual_rain") else None,
                            "note": "Normal is too small to compute a meaningful deficit (dry season)." if defr is None else ""}
        else:
            anom_raw = n14 = defr = None; warn.append("Climate normals could not be retrieved, so heat and rainfall anomalies and risk scores are unavailable. Observed and forecast data are shown."); data["heat"] = {"max7": round(max(t_next), 1), "mean7": round(mean(t_next), 1)}
            data["rain"] = {"past14": round(sum(p_past), 1), "next7": round(sum(p_next), 1), "max_day": round(max(p_next), 1) if p_next else None, "prob_max": max(pr_next) if pr_next else None}
        row("Rainfall forecast (next 7 days)", round(sum(p_next), 1), "mm", "Forecast", S_FC, ctime)
        storm = max(max(p_next) if p_next else 0, 5.0); imp = imp_pop(pl.get("population")); imp_used = imp if imp is not None else .45
        row("Storm rainfall used for flood index", round(storm, 1), "mm/day", "Forecast", S_FC, ctime, "Highest forecast daily rainfall, minimum 5 mm")
        row("Impervious cover used", round(imp_used*100), "%", "Model estimate", "Proxy from population size" if imp is not None else "Default assumption", now, "Not surveyed; drainage capacity is modelled")
        rd = clean((fl.get("daily") or {}).get("river_discharge", [])) if flood_ok else []
        if rd:
            data["river"] = {"peak": round(max(rd[-7:]), 1), "mean": round(mean(rd), 1), "ratio": round(max(rd[-7:])/mean(rd), 2) if mean(rd) > 0 else None, "unit": "m³/s"}
            row("River discharge, forecast peak", data["river"]["peak"], "m³/s", "Forecast", S_FL, ctime, "Nearest river grid cell (~5 km); not a flood warning")
        else: row("River discharge", None, "m³/s", "Unavailable", S_FL, None, "No river-discharge cell for this location or the service did not respond")
        if e_past and e_next:
            bal = sum(p_past) - sum(e_past); data["water"] = {"et0_14d": round(sum(e_past), 1), "balance_14d": round(bal, 1), "balance_next7": round(sum(p_next) - sum(e_next), 1)}
            row("Water balance, last 14 days (rain minus evapotranspiration)", round(bal, 1), "mm", "Observed", S_FC, ctime, "Negative means the land is drying out")
        if sm: data.setdefault("water", {})["soil_moisture"] = round(mean(sm), 3); row("Soil moisture (0-7 cm, 14-day mean)", round(mean(sm), 3), "m³/m³", "Observed", S_FC, ctime, "Model analysis")
        else: warn.append("Soil-moisture data is unavailable; the vegetation proxy uses a neutral value.")
        if gwi: data["groundwater"] = {"available": True, "stage": gwi["stage"], "category": "Over-exploited" if gwi["stage"] > 100 else "Safe/Semi-critical/Critical", "source": gwi["source"], "area": gwi["area"], "dist_km": gwi["dist_km"]}; row("Groundwater stage of extraction", gwi["stage"], "%", "Historical", gwi["source"], "CGWB 2024 assessment", f"Applied within {gwi['dist_km']} km of the {gwi['area']} reference area")
        else: data["groundwater"] = {"available": False, "note": "No reliable groundwater data is loaded for this location."}; row("Groundwater", None, "", "Unavailable", "No source loaded", None, "Neutral value 30 assumed in the model; uncertainty widened"); warn.append("Groundwater data is unavailable here. The model assumed a neutral groundwater index and its uncertainty was widened.")
        row("Water-demand growth", None, "", "Model estimate", "Modelled assumption", now, "No local demand data; 3.5 points per °C of heat anomaly (Gurugram area uses reported figures)")
        data["provenance"] = prov
        # chart series
        data["chart"] = {"dates": d["time"][:21], "tmax": d["temperature_2m_max"][:21], "tmin": d.get("temperature_2m_min", [])[:21], "precip": d["precipitation_sum"][:21], "split": 14, "units": {"temp": "°C", "precip": "mm"}}
        lim += ["Open-Meteo 'observed' values are weather-model analyses on a grid (about 2 to 11 km), not readings from a specific station.",
                "Risk scores are experimental estimates from a model trained on simulated data. They are not verified real-world forecasts or official warnings.",
                "Flood risk is a rule-based runoff-versus-drainage index with modelled imperviousness and drainage. River discharge is shown separately and is not a flood warning.",
                "Water demand and vegetation cover are modelled or proxy values; no local consumption or land-cover data is loaded."]
        if not gwi: lim.append("Groundwater is unavailable for this location.")
        data["limitations"] = lim; data["warnings"] = warn
        # model inputs (validated against the training ranges)
        if not clim_ok: return data, None
        anom = float(np.clip(anom_raw, 0, 6)); deficit = 0.0 if defr is None else float(np.clip(defr, -20, 60))
        in_gurugram = gwi is not None and gwi["area"] in ("Gurugram", "Sohna", "Manesar") and hav(lat, lon, 28.46, 77.03) <= 30
        dem_raw = m.demand_ref(mean(t_next)) if in_gurugram else 3.5*max(anom_raw, 0); demand = float(np.clip(dem_raw, -30, 50))
        veg = float(np.clip(mean(sm)/0.25, .6, 1.2)) if sm else 1.0; green = float(np.clip(30*veg, 10, 60)); gw = float(np.clip(gwi["stage"]/4, 0, 100)) if gwi else 30.0
        feats = [("Temperature anomaly", anom_raw, anom, "°C above normal", "0 to 6", "Forecast vs historical normal"), ("Rainfall deficit", defr if defr is not None else 0, deficit, "% below normal", "-20 to 60", "Observed vs historical normal" if defr is not None else "Dry season: set to 0"),
                 ("Water-demand growth", dem_raw, demand, "% above requirement", "-30 to 50", "Reported figures (GMDA/MCG)" if in_gurugram else "Modelled assumption"), ("Green cover", 30*veg, green, "% vegetated", "10 to 60", "Soil-moisture proxy"),
                 ("Groundwater stress", gw, gw, "index (stage / 4)", "0 to 100", "CGWB-based" if gwi else "Neutral assumption (unavailable)")]
        for nme, raw, used, unit, rng, src in feats: val.append({"feature": nme, "raw": round(float(raw), 2), "used": round(used, 2), "unit": unit, "trained_range": rng, "clipped": abs(float(raw) - used) > 1e-6, "source": src})
        meta = {"inputs": [anom, deficit, demand, green, gw], "imp": imp_used, "storm": storm, "rain_annual": cl.get("annual_rain") or 800.0, "gw_known": gwi is not None, "demand_known": in_gurugram, "validation": val, "warnings": warn}
        return data, meta

    def register(pl, label, data, meta):
        with LOCK:
            old = GEO.get(label)
            if old and hav(old["lat"], old["lon"], pl["lat"], pl["lon"]) > 5: label += f" ({pl['lat']:.2f}, {pl['lon']:.2f})"
            GEO[label] = {**meta, "label": label, "lat": pl["lat"], "lon": pl["lon"], "ts": time.time(), "place": pl, "inputs_meta": data["provenance"]}; GEO.move_to_end(label)
            while len(GEO) > EVICT_AT:
                k, _ = GEO.popitem(last=False); m.SC.pop(k, None)
        f = m.clipf(meta["inputs"]); sc = {**m.score(f), **m.indices(label, f), **m.uncertainty(f, label), "future7": m.future7(f)}; m.SC[label] = sc
        return label, sc
    def summary(label, sc, data, meta):
        h, r, fl = data.get("heat", {}), data.get("rain", {}), data.get("river")
        s = [f"{label}: the experimental Nexus estimate is {sc['level']} ({sc['nexus']}/100, confidence {sc['conf']}%)."]
        s.append(f"Heat is {sc['heat_level']} ({sc['heat']}): the forecast maximum is {h.get('max7')}°C" + (f", {h['anomaly']:+.1f}°C against the normal for this time of year." if h.get("anomaly") is not None else "."))
        s.append(f"Flood exposure is {sc['flood_level']} ({sc['flood']}) for a {meta['storm']:g} mm/day storm" + (f"; the river-discharge forecast peaks at {fl['peak']} m³/s." if fl else "; no river-discharge data is available."))
        s.append(f"Water scarcity is {sc['scar_level']} ({sc['scarcity']}); rainfall in the last 14 days was {r.get('past14')} mm" + (f" against a normal of {r['normal14']} mm." if r.get("normal14") is not None else "."))
        if not meta["gw_known"]: s.append("Groundwater data is unavailable, so a neutral value was assumed and the uncertainty is wider.")
        return " ".join(s)

    def parse_place(j, lat, lon):
        pl = {"name": j.get("name"), "admin1": j.get("admin1"), "admin2": j.get("admin2"), "country": j.get("country"), "country_code": j.get("country_code"), "population": j.get("population") if fin(j.get("population")) else None,
              "elevation": j.get("elevation"), "timezone": j.get("timezone"), "lat": lat, "lon": lon}
        return pl
    @app.route("/api/location-data")
    def location_data():
        c = parse_coord(request.args.get("lat"), request.args.get("lon"))
        if not c: return err("bad_coordinates", "Latitude must be between -90 and 90 and longitude between -180 and 180.", 400)
        if limited("data", 30, 60): return err("rate_limited", "Too many requests. Please wait a moment.", 429)
        b = bundle(c[0], c[1], request.args.get("refresh") == "1"); pl = {"name": request.args.get("name"), "lat": c[0], "lon": c[1], "country_code": request.args.get("country_code"), "population": None}
        try: data, meta = derive(c[0], c[1], pl, b)
        except ProviderError as e: return err(e.kind, e.msg, e.status if e.status in (429, 502, 503, 504) else 502)
        return jsonify({"lat": c[0], "lon": c[1], "name": pl["name"], "data": data, "risk_ready": meta is not None})

    @app.route("/api/location-risk", methods=["POST"])
    def location_risk():
        j = request.get_json(silent=True) or {}; c = parse_coord(j.get("lat"), j.get("lon"))
        if not c: return err("bad_coordinates", "Latitude must be between -90 and 90 and longitude between -180 and 180.", 400)
        if limited("risk", 24, 60): return err("rate_limited", "Too many location requests. Please wait a moment.", 429)
        lat, lon = c; pl = parse_place(j, lat, lon); label = (str(j.get("name") or "")[:120]).strip()
        if not label:
            rp, label = reverse(lat, lon); pl.update({k: v for k, v in rp.items() if v})
        b = bundle(lat, lon, bool(j.get("refresh")))
        try: data, meta = derive(lat, lon, pl, b)
        except ProviderError as e: return err(e.kind, e.msg + " Please try again.", e.status if e.status in (429, 502, 503, 504) else 502)
        base = {"location": {"label": label, "lat": lat, "lon": lon, "elevation": data.get("elevation") or pl.get("elevation"), "timezone": data.get("timezone"), "country": pl.get("country"), "admin1": pl.get("admin1"), "admin2": pl.get("admin2"), "population": pl.get("population")}, "data": data}
        if meta is None: return jsonify({**base, "risk": None, "unavailable": "Climate normals could not be retrieved for this location, so risk scores are unavailable. Observed and forecast data are shown."})
        label, sc = register(pl, label, data, meta); base["location"]["label"] = label
        risk = {"name": label, "x": 50, "y": 50, "geo": True, "lat": lat, "lon": lon, "inputs": [round(x, 2) for x in meta["inputs"]], "rainfall": int(np.clip(meta["rain_annual"], 200, 1500)), **sc}
        recs = [{"title": z["title"], "why": z["why"], "urgency": z["urgency"], "audience": z["audience"]} for z in m.plan_for(label)[:4]]
        return jsonify({**base, "risk": risk, "validation": meta["validation"], "summary": summary(label, sc, data, meta), "recommendations": recs,
                        "assumptions": ["Rainfall deficit and heat anomaly compare recent data with a 10-year normal for this time of year.", "Demand growth, green cover and imperviousness are modelled or proxy values.", "Values outside the model's training range are clipped and flagged in the validation table."]})
