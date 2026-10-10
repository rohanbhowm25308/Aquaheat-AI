import json, os
import joblib
import numpy as np

def model_fn(model_dir): return joblib.load(os.path.join(model_dir, "model.joblib"))
def input_fn(body, content_type): return np.array(json.loads(body)["instances"], dtype=float)
def predict_fn(x, model): return model.predict(x)
def output_fn(pred, accept): return json.dumps({"predictions": [float(v) for v in pred]}), "application/json"
