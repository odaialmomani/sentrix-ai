import joblib, pandas as pd, time, requests

MODEL  = r"C:\Users\USER\Desktop\model_py37.pkl"
SCALER = r"C:\Users\USER\Desktop\scaler_py37.pkl"
CSV    = r"C:\Users\USER\Desktop\presentation_samples.csv"
API    = "http://localhost:5001/api/update"
FEATS  = ['CAN_ID','DLC','D0','D1','D2','D3','D4','D5','D6','D7']

model  = joblib.load(MODEL)
scaler = joblib.load(SCALER)
df     = pd.read_csv(CSV)

print(f"SENTRIX AI System — {len(df)} samples loaded")

while True:
    for _, row in df.iterrows():
        t0   = time.time()
        pred = model.predict(scaler.transform(row[FEATS].values.reshape(1,-1)))[0]
        det  = round((time.time()-t0)*1000, 2)
        try:
            requests.post(API, json={"ml_pred":pred,"real_label":row["label"],
                                     "detection_time":det,"can_id":str(row["CAN_ID"])}, timeout=2)
        except: pass
        print(f"[{pred}] CAN:{row['CAN_ID']} | Real:{row['label']} | {det}ms")
        time.sleep(1)
