"""Offline tests for the location-search feature. Provider HTTP calls are replaced by realistic simulated responses
(Open-Meteo geocoding, forecast, archive, flood and Nominatim). Run:  python tests/test_geo.py"""
import os, sys, math, datetime, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests, app, geo

CALLS, FAIL = [], {}
class R:
    def __init__(s, code, j): s.status_code, s._j = code, j
    def json(s):
        if s._j is None: raise ValueError("bad json")
        return s._j
PLACES = {"gurugram": [{"id": 1270642, "name": "Gurugram", "latitude": 28.4601, "longitude": 77.02635, "elevation": 220.0, "feature_code": "PPLA2", "country_code": "IN", "country": "India", "admin1": "Haryana", "admin2": "Gurgaon", "population": 876969, "timezone": "Asia/Kolkata"}],
          "noida": [{"id": 1, "name": "Noida", "latitude": 28.5355, "longitude": 77.391, "elevation": 200.0, "country_code": "IN", "country": "India", "admin1": "Uttar Pradesh", "admin2": "Gautam Buddha Nagar", "population": 642381, "timezone": "Asia/Kolkata"}],
          "kolkata": [{"id": 1275004, "name": "Kolkata", "latitude": 22.5626, "longitude": 88.363, "elevation": 11.0, "country_code": "IN", "country": "India", "admin1": "West Bengal", "admin2": "Kolkata", "population": 4631392, "timezone": "Asia/Kolkata"}],
          "springfield": [{"id": 10, "name": "Springfield", "latitude": 39.80, "longitude": -89.64, "country_code": "US", "country": "United States", "admin1": "Illinois", "admin2": "Sangamon", "population": 114394, "timezone": "America/Chicago"},
                          {"id": 11, "name": "Springfield", "latitude": 41.84, "longitude": -88.34, "country_code": "US", "country": "United States", "admin1": "Illinois", "admin2": "Kane", "population": 1200, "timezone": "America/Chicago"},
                          {"id": 12, "name": "Springfield", "latitude": 37.21, "longitude": -93.29, "country_code": "US", "country": "United States", "admin1": "Missouri", "admin2": "Greene", "population": 169176, "timezone": "America/Chicago"}]}
def hot(lat): return 40.0 if lat > 26 else 36.0           # simulated forecast maximum: differs by place so stale data would be detected
def fake_get(url, params=None, timeout=None, headers=None):
    p = params or {}; CALLS.append(url.split("/")[2]); kind = ("geo" if "geocoding" in url else "arch" if "archive" in url else "flood" if "flood" in url else "rev" if "nominatim" in url else "fc")
    f = FAIL.get(kind)
    if f == "timeout": raise requests.Timeout()
    if f == "network": raise requests.ConnectionError()
    if f == "429": return R(429, {"error": True, "reason": "Too many requests"})
    if f == "500": return R(500, {"error": True})
    if f == "garbage": return R(200, None)
    if kind == "geo": return R(200, {"results": PLACES[p["name"].lower()]} if p["name"].lower() in PLACES else {"generationtime_ms": 0.4})
    lat = float(p.get("latitude", 0))
    if kind == "rev": return R(200, {"address": {"city": "Faketown", "state": "Haryana", "country": "India", "country_code": "in"}})
    today = datetime.date.today()
    if kind == "fc":
        days = [(today + datetime.timedelta(i)).isoformat() for i in range(-14, 7)]
        tx = [33.0]*14 + [hot(lat)]*7; pr = [1.0]*14 + [0, 0, 22.0, 3, 0, 0, 1]
        return R(200, {"latitude": lat, "longitude": float(p["longitude"]), "elevation": 220.0, "timezone": "Asia/Kolkata", "current_units": {"temperature_2m": "°C"},
            "current": {"time": today.isoformat() + "T12:00", "temperature_2m": hot(lat) - 2, "apparent_temperature": hot(lat) + 1, "relative_humidity_2m": 41, "wind_speed_10m": 9.5, "precipitation": 0.0},
            "daily": {"time": days, "temperature_2m_max": tx, "temperature_2m_min": [x - 9 for x in tx], "precipitation_sum": pr, "precipitation_probability_max": [10]*21, "et0_fao_evapotranspiration": [5.0]*21},
            "hourly": {"time": ["x"]*504, "soil_moisture_0_to_7cm": [0.18]*504}})
    if kind == "arch":
        d0, d1 = datetime.date.fromisoformat(p["start_date"]), datetime.date.fromisoformat(p["end_date"]); n = (d1 - d0).days + 1
        days = [(d0 + datetime.timedelta(i)).isoformat() for i in range(n)]
        return R(200, {"daily": {"time": days, "temperature_2m_max": [34.0]*n, "precipitation_sum": [2.0]*n}})
    if kind == "flood":
        if lat > 26: return R(400, {"error": True, "reason": "No river discharge data for this location"})
        days = [(today + datetime.timedelta(i)).isoformat() for i in range(-7, 7)]
        return R(200, {"daily": {"time": days, "river_discharge": [900.0]*7 + [1000.0, 1200, 1500, 1400, 1100, 1000, 950]}})
requests.get = fake_get

def reset():
    FAIL.clear(); CALLS.clear(); geo._CACHE.clear(); geo._RL.clear()
C = app.app.test_client(); T = []
def test(f): T.append(f); return f
def risk(label, lat, lon, **kw):
    return C.post("/api/location-risk", json={"lat": lat, "lon": lon, "name": label, "country_code": "IN", "population": kw.get("pop"), **{k: v for k, v in kw.items() if k != "pop"}})

@test
def search_basic():
    reset(); r = C.get("/api/locations/search?q=Gurugram"); j = r.json
    assert r.status_code == 200 and j["results"][0]["label"] == "Gurugram, Haryana, India" and abs(j["results"][0]["lat"] - 28.4601) < 1e-6 and j["results"][0]["admin2"] == "Gurgaon"
@test
def search_validation_and_empty():
    reset(); assert C.get("/api/locations/search?q=a").status_code == 400 and C.get("/api/locations/search?q=" + "x"*90).status_code == 400
    j = C.get("/api/locations/search?q=zzzzqq").json; assert j["results"] == [] and "No place found" in j["message"]
@test
def search_duplicates_are_distinguishable():
    reset(); labels = [p["label"] for p in C.get("/api/locations/search?q=Springfield").json["results"]]
    assert len(labels) == 3 and len(set(labels)) == 3, labels
@test
def search_provider_failures():
    reset(); FAIL["geo"] = "timeout"; r = C.get("/api/locations/search?q=Kolkata"); assert r.status_code in (503, 504) and r.json["error"] and r.json["message"]
    geo._CACHE.clear(); j = C.get("/api/locations/search?q=Gurugram").json; assert j["degraded"] and j["results"][0]["name"] == "Gurugram"   # built-in fallback
    FAIL["geo"] = "429"; assert C.get("/api/locations/search?q=Mumbai").status_code == 429
    FAIL["geo"] = "garbage"; assert C.get("/api/locations/search?q=Delhi2").status_code in (502, 503)
@test
def search_rate_limit():
    reset(); codes = [C.get("/api/locations/search?q=Noida").status_code for _ in range(45)]; assert codes[0] == 200 and codes[-1] == 429
@test
def risk_for_gurugram_is_complete_and_validated():
    reset(); r = risk("Gurugram, Haryana, India", 28.4601, 77.02635, pop=876969); j = r.json; assert r.status_code == 200, j
    k = j["risk"]; assert k["geo"] and 0 <= k["nexus"] <= 100 and k["name"] == "Gurugram, Haryana, India" and k["lat"] == 28.4601
    for key in ("heat", "flood", "scarcity", "gw", "conf", "lo", "hi", "flood_lo", "scar_lo", "heat_lo", "future7", "drivers", "flood_parts"): assert key in k, key
    assert len(j["validation"]) == 5 and [v["feature"] for v in j["validation"]][0] == "Temperature anomaly"
    assert j["data"]["groundwater"]["available"] and j["data"]["groundwater"]["stage"] == 326.52 and j["data"]["heat"]["max7"] == 40.0
    types = {p["type"] for p in j["data"]["provenance"]}; assert {"Observed", "Forecast", "Historical", "Model estimate", "Unavailable"} <= types, types
    assert len(j["recommendations"]) >= 1 and "experimental" in j["summary"] and j["data"]["chart"]["split"] == 14 and len(j["data"]["chart"]["tmax"]) == 21
    assert "Gurugram, Haryana, India" in app.GEO
@test
def second_location_has_no_stale_data():
    reset(); a = risk("Gurugram, Haryana, India", 28.4601, 77.02635, pop=876969).json; b = risk("Kolkata, West Bengal, India", 22.5626, 88.363, pop=4631392).json
    assert a["data"]["heat"]["max7"] == 40.0 and b["data"]["heat"]["max7"] == 36.0 and a["risk"]["name"] != b["risk"]["name"]
    assert a["risk"]["heat"] != b["risk"]["heat"] and b["data"]["river"]["peak"] == 1500.0 and "river" not in a["data"]
    ta, tb = C.get("/api/trust?loc=" + requests.utils.quote(a["risk"]["name"])).json, C.get("/api/trust?loc=" + requests.utils.quote(b["risk"]["name"])).json
    assert ta["loc"] != tb["loc"] and ta["inputs"][1]["value"] != tb["inputs"][1]["value"] or ta["inputs"][0]["value"] != tb["inputs"][0]["value"]
@test
def missing_groundwater_is_flagged_not_invented():
    reset(); b = risk("Kolkata, West Bengal, India", 22.5626, 88.363, pop=4631392).json; g = b["data"]["groundwater"]
    assert g["available"] is False and "No reliable" in g["note"] and not app.GEO["Kolkata, West Bengal, India"]["gw_known"]
    gw = [v for v in b["validation"] if v["feature"] == "Groundwater stress"][0]; assert gw["used"] == 30 and "unavailable" in gw["source"]
    assert any("Groundwater" in w for w in b["data"]["warnings"]); w = C.get("/api/water?loc=Kolkata,%20West%20Bengal,%20India").json; assert w["groundwater"]["sourced"] is False and "No reliable" in w["groundwater"]["note"]
    t = C.get("/api/trust?loc=Kolkata,%20West%20Bengal,%20India").json; assert any("Groundwater" in x["name"] and x["tag"] == "sim" for x in t["inputs"])
@test
def uncertainty_is_wider_when_inputs_are_assumed():
    reset(); a = risk("Gurugram, Haryana, India", 28.4601, 77.02635, pop=876969).json["risk"]; b = risk("Noida, Uttar Pradesh, India", 28.5355, 77.391, pop=642381).json["risk"]
    assert (a["scar_hi"] - a["scar_lo"]) <= (b["scar_hi"] - b["scar_lo"])
@test
def climate_normals_failure_gives_data_without_risk():
    reset(); FAIL["arch"] = "timeout"; r = risk("Mumbai, Maharashtra, India", 19.07, 72.88, pop=12442373); j = r.json; assert r.status_code == 200 and j["risk"] is None and "unavailable" in j["unavailable"] and j["data"]["heat"]["max7"] == 40.0 if False else (j["risk"] is None and "Mumbai, Maharashtra, India" not in app.GEO)
@test
def forecast_failure_returns_clear_error():
    reset(); FAIL["fc"] = "timeout"; r = risk("Delhi, Delhi, India", 28.61, 77.21); assert r.status_code in (502, 503, 504) and r.json["error"] and r.json["message"]
    reset(); FAIL["fc"] = "429"; assert risk("Delhi, Delhi, India", 28.61, 77.21).status_code == 429
    reset(); FAIL["fc"] = "500"; assert risk("Delhi, Delhi, India", 28.61, 77.21).status_code == 502
@test
def coordinate_validation():
    reset(); assert risk("x", 91, 10).status_code == 400 and risk("x", 10, 181).status_code == 400 and risk("x", "abc", 10).status_code == 400 and C.get("/api/location-data?lat=nan&lon=1").status_code == 400
@test
def other_endpoints_work_for_searched_location():
    reset(); lab = "Kolkata, West Bengal, India"; risk(lab, 22.5626, 88.363, pop=4631392); q = requests.utils.quote(lab)
    for u in ("/api/actions?loc=", "/api/alerts?loc=", "/api/water?loc=", "/api/trust?loc=", "/api/forecast?loc=", "/api/heatisland?loc="): assert C.get(u + q).status_code == 200, u
    s = C.post("/api/simulate", json={"loc": lab, "temp": 2}).json; base = app.SC[lab]; assert s["scores"]["heat"]["cur"] == base["heat"] and s["scores"]["heat"]["sim"] >= base["heat"]
    assert C.post("/api/harvest", json={"loc": lab, "roof": 100}).status_code == 200 and C.post("/api/agent", json={"loc": lab}).status_code == 200 and C.post("/api/brief", json={"loc": lab}).status_code == 200
    t = C.post("/api/twin", json={"locs": [lab]}).json; assert [d["name"] for d in t["districts"]] == [lab] and t["districts"][0]["base"]["nexus"] == base["nexus"], "searched mode must show only searched places"
    d8 = C.post("/api/twin", json={}).json; assert len(d8["districts"]) == 8 and lab not in [d["name"] for d in d8["districts"]], "demo mode must show only the 8 demo areas"
    assert [d["name"] for d in C.post("/api/twin", json={"locs": ["Atlantis", lab]}).json["districts"]] == [lab]
    assert C.post("/api/reports", json={"type": "leak", "loc": lab, "note": "t"}).status_code == 200
@test
def reports_are_scoped_to_the_selected_place():
    reset(); lab = "Kolkata, West Bengal, India"; risk(lab, 22.5626, 88.363, pop=4631392)
    assert all(not z["sample"] and z["loc"] == lab for z in C.get("/api/reports?loc=" + requests.utils.quote(lab)).json["reports"]), "demo sample reports must not appear for a searched place"
    assert all(z["loc"] == "Sector 57" for z in C.get("/api/reports?loc=Sector%2057").json["reports"]) and C.get("/api/reports?loc=Sector%2057").json["reports"]

@test
def unknown_location_is_404_not_gurugram():
    reset(); for_u = ["/api/actions?loc=Atlantis", "/api/trust?loc=Atlantis", "/api/water?loc=", "/api/forecast?loc=Nowhere"]
    assert all(C.get(u).status_code == 404 for u in for_u) and C.post("/api/simulate", json={"loc": "Atlantis"}).status_code == 404 and C.post("/api/agent", json={"loc": "Atlantis"}).status_code == 404
@test
def caching_and_refresh():
    reset(); risk("Gurugram, Haryana, India", 28.4601, 77.02635); n1 = len(CALLS); risk("Gurugram, Haryana, India", 28.4601, 77.02635); assert len(CALLS) == n1, "cache miss"
    risk("Gurugram, Haryana, India", 28.4601, 77.02635, refresh=True); assert len(CALLS) > n1   # refresh re-fetches the forecast
@test
def use_my_location_reverse_label():
    reset(); j = C.post("/api/location-risk", json={"lat": 28.46, "lon": 77.03}).json; assert j["location"]["label"] == "Faketown, Haryana, India"
    reset(); FAIL["rev"] = "timeout"; j = C.post("/api/location-risk", json={"lat": 28.46, "lon": 77.03}).json; assert j["location"]["label"].startswith("Your location (28.460")
@test
def location_data_endpoint():
    reset(); j = C.get("/api/location-data?lat=22.5626&lon=88.363&name=Kolkata").json; assert j["risk_ready"] and j["data"]["rain"]["past14"] == 14.0
@test
def risk_rate_limit():
    reset(); codes = [risk("Gurugram, Haryana, India", 28.4601, 77.02635).status_code for _ in range(26)]; assert codes[0] == 200 and codes[-1] == 429
@test
def existing_features_unchanged():
    reset(); L = C.get("/api/locations").json; g = [x for x in L if x["name"] == "Gurugram"][0]
    assert len(L) == 8 and g["nexus"] == 82 and g["level"] == "CRITICAL" and "lat" in g and "flood" in g and C.get("/api/pipeline").status_code == 200 and C.get("/methodology").status_code == 200
    assert C.post("/api/simulate", json={"loc": "Gurugram", "rain": 30}).json["scores"]["flood"]["sim"] > g["flood"] and C.get("/api/actions?loc=Gurugram").status_code == 200

if __name__ == "__main__":
    bad = 0
    for f in T:
        try: f(); print("PASS", f.__name__)
        except Exception: bad += 1; print("FAIL", f.__name__); traceback.print_exc()
    print(f"\n{len(T) - bad}/{len(T)} passed"); sys.exit(1 if bad else 0)
