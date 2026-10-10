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
