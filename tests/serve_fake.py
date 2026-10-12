"""Run the app locally with SIMULATED location providers (no internet needed) to try the search UI offline:  python tests/serve_fake.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_geo, app
if __name__ == "__main__":
    print("Offline demo with simulated providers on http://127.0.0.1:5055  (search: Gurugram, Noida, Kolkata, Springfield)")
    app.app.run(host="127.0.0.1", port=5055, debug=False, threaded=True)
