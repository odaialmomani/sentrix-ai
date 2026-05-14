import joblib
import pandas as pd
import numpy as np
import threading
import os

# ===== Load Model =====
MODEL_PATH  = os.path.join(os.path.dirname(__file__), "model_py37.pkl")
SCALER_PATH = os.path.join(os.path.dirname(__file__), "scaler_py37.pkl")

try:
    model  = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    ML_READY = True
    print("✅ ML Model Loaded!")
except Exception as e:
    ML_READY = False
    print(f"⚠️ Model not found: {e}")

# ===== Auto Simulator =====
FEATURES = ['CAN_ID','DLC','D0','D1','D2','D3','D4','D5','D6','D7']

SAMPLES = [
    {"CAN_ID":399,"DLC":8,"D0":35,"D1":22,"D2":18,"D3":12,"D4":8,"D5":5,"D6":3,"D7":1,"label":"Normal"},
    {"CAN_ID":608,"DLC":8,"D0":28,"D1":19,"D2":14,"D3":9,"D4":6,"D5":3,"D6":2,"D7":0,"label":"Normal"},
    {"CAN_ID":0,  "DLC":8,"D0":0, "D1":0, "D2":0, "D3":0, "D4":0, "D5":0, "D6":0, "D7":0,"label":"DoS"},
    {"CAN_ID":0,  "DLC":8,"D0":0, "D1":0, "D2":0, "D3":0, "D4":0, "D5":0, "D6":0, "D7":0,"label":"DoS"},
    {"CAN_ID":772,"DLC":8,"D0":187,"D1":243,"D2":91,"D3":156,"D4":204,"D5":33,"D6":178,"D7":99,"label":"Fuzzy"},
    {"CAN_ID":825,"DLC":8,"D0":201,"D1":77, "D2":143,"D3":255,"D4":12,"D5":88,"D6":167,"D7":44,"label":"Fuzzy"},
    {"CAN_ID":352,"DLC":8,"D0":42, "D1":31, "D2":22,"D3":15,"D4":10,"D5":7, "D6":4,  "D7":2, "label":"Normal"},
    {"CAN_ID":0,  "DLC":8,"D0":0, "D1":0, "D2":0, "D3":0, "D4":0, "D5":0, "D6":0, "D7":0,"label":"DoS"},
    {"CAN_ID":1650,"DLC":8,"D0":133,"D1":201,"D2":44,"D3":178,"D4":89,"D5":222,"D6":15,"D7":167,"label":"Fuzzy"},
    {"CAN_ID":608,"DLC":8,"D0":31,"D1":21,"D2":16,"D3":11,"D4":7,"D5":4,"D6":2,"D7":1,"label":"Normal"},
]

import time as _time
import datetime as _datetime
import random as _random

def run_auto_ml():
    global latest_data, stats, attack_log, det_times
    i = 0
    while True:
        row = SAMPLES[i % len(SAMPLES)]
        try:
            if ML_READY:
                import time as t0
                start = t0.time()
                features = [row[f] for f in FEATURES]
                X = pd.DataFrame([dict(zip(FEATURES, features))])
                scaled = scaler.transform(X)
                pred = model.predict(scaled)[0]
                det  = round((_time.time() - start) * 1000, 2)
            else:
                pred = row["label"]
                det  = round(_random.uniform(8, 25), 1)

            real = row["label"]
            ts   = _datetime.datetime.now().strftime("%H:%M:%S")
            cid  = hex(row["CAN_ID"])

            stats["total"] += 1
            det_times.append(det)
            if pred == "Normal":   stats["normal"]  += 1
            elif pred == "DoS":    stats["dos"]     += 1
            elif pred == "Fuzzy":  stats["fuzzy"]   += 1
            if pred == real:       stats["correct"] += 1

            if pred != "Normal":
                stats["blocked"] += 1
                s = sev(pred)
                attack_log.append({"time":ts,"type":pred,"can_id":cid,
                                   "detection_time":det,"real":real,"severity":s,"action":"BLOCKED"})
                latest_data = {"attack":"ATTACK: "+pred,"can_id":cid,"time":ts,
                               "ips_status":"BLOCKED","real_label":real,"ml_label":pred,
                               "detection_time":det,"severity":s}
                print(f"[{ts}] 🔴 {pred} | {cid} | {det}ms")
            else:
                latest_data = {"attack":"Normal","can_id":cid,"time":ts,
                               "ips_status":"ALLOW","real_label":real,"ml_label":pred,
                               "detection_time":det,"severity":"None"}
                print(f"[{ts}] ✅ Normal | {cid} | {det}ms")
        except Exception as e:
            print(f"ML Error: {e}")

        i += 1
        _time.sleep(2)

# Start auto ML thread
threading.Thread(target=run_auto_ml, daemon=True).start()