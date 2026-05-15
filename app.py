from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import datetime
import random as _random
import joblib
import pandas as pd
import time

app = Flask(__name__)
app.secret_key = "sentrix_ai_v2_2024"

# ===== USERS =====
USERS = {
    "admin":   {"password": "admin123",   "role": "Admin",   "name": "Admin User"},
    "analyst": {"password": "analyst123", "role": "Analyst", "name": "Security Analyst"},
    "viewer":  {"password": "viewer123",  "role": "Viewer",  "name": "Viewer"},
}

# ===== SYSTEM STATE =====
system_running = {"status": True}

latest_data = {
    "attack": "Normal", "can_id": "--", "time": "--:--:--",
    "ips_status": "Monitoring", "real_label": "-", "ml_label": "-",
    "detection_time": 0, "severity": "None"
}

stats = {"total": 0, "normal": 0, "dos": 0, "fuzzy": 0, "correct": 0, "blocked": 0}

attack_log = []
traffic_log = []
det_times  = []

# ===== LOAD MODEL =====
model  = joblib.load("model_py37.pkl")
scaler = joblib.load("scaler_py37.pkl")
df = pd.read_csv("presentation_samples.csv")

counter = {"i": 0}

# ===== HELPERS =====
def sev(t):
    return "Critical" if t == "DoS" else "High" if t == "Fuzzy" else "None"

def auth(f):
    from functools import wraps
    @wraps(f)
    def w(*a, **k):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*a, **k)
    return w

def admin_only(f):
    from functools import wraps
    @wraps(f)
    def w(*a, **k):
        if "user" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "Admin":
            return "Access Denied", 403
        return f(*a, **k)
    return w

def ctx():
    return dict(
        user=session.get("name",""),
        role=session.get("role",""),
        running=system_running["status"],
        log_count=len(attack_log)
    )

# ===== ROUTES =====
@app.route("/", methods=["GET","POST"])
def login():
    error = ""
    if request.method == "POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","")
        if u in USERS and USERS[u]["password"] == p:
            session.update(user=u, role=USERS[u]["role"], name=USERS[u]["name"])
            return redirect(url_for("dashboard"))
        error = "Invalid credentials"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@auth
def dashboard():
    acc = round(stats["correct"] / max(stats["total"], 1) * 100, 1)
    return render_template("dashboard.html", **ctx(),
                           stats=stats, latest=latest_data, accuracy=acc)

@app.route("/monitor")
@auth
def monitor():
    return render_template("monitor.html", **ctx(),
                           latest=latest_data, stats=stats)

@app.route("/logs")
@auth
def logs():
    return render_template("logs.html", **ctx(),
                           logs=list(reversed(attack_log)))

@app.route("/analytics")
@auth
def analytics():
    acc = round(stats["correct"] / max(stats["total"], 1) * 100, 1)
    return render_template("analytics.html", **ctx(),
                           stats=stats, logs=attack_log,
                           accuracy=acc, latest=latest_data)

# 🔥 NEW TRAFFIC PAGE
@app.route("/traffic")
@auth
def traffic():
    return render_template("traffic.html", **ctx(),
                           traffic=list(reversed(traffic_log)))

@app.route("/admin")
@admin_only
def admin():
    return render_template("admin.html", **ctx(),
                           stats=stats, users=USERS)

@app.route("/about")
@auth
def about():
    return render_template("about.html", **ctx())

# ===== API =====
@app.route("/api/status")
@auth
def api_status():
    global latest_data, stats, attack_log, traffic_log, det_times, counter

    if system_running["status"]:
        row = df.iloc[counter["i"] % len(df)]

        start = time.time()

        features = pd.DataFrame([[
            row['CAN_ID'], row['DLC'],
            row['D0'], row['D1'], row['D2'], row['D3'],
            row['D4'], row['D5'], row['D6'], row['D7']
        ]], columns=[
            'CAN_ID','DLC','D0','D1','D2','D3','D4','D5','D6','D7'
        ])

        scaled = scaler.transform(features)
        pred   = model.predict(scaled)[0]

        det = round((time.time() - start) * 1000, 2)

        real = row["label"]
        cid  = row["CAN_ID"]
        ts   = datetime.datetime.now().strftime("%H:%M:%S")

        stats["total"] += 1
        det_times.append(det)

        if pred == "Normal":   stats["normal"] += 1
        elif pred == "DoS":    stats["dos"] += 1
        elif pred == "Fuzzy":  stats["fuzzy"] += 1

        if pred == real:
            stats["correct"] += 1

        if pred != "Normal":
            stats["blocked"] += 1

            s = sev(pred)

            attack_log.append({
                "time": ts,
                "type": pred,
                "can_id": str(cid),
                "detection_time": det,
                "real": real,
                "severity": s,
                "action": "BLOCKED"
            })

            latest_data = {
                "attack": "ATTACK: " + pred,
                "can_id": str(cid),
                "time": ts,
                "ips_status": "BLOCKED",
                "real_label": real,
                "ml_label": pred,
                "detection_time": det,
                "severity": s
            }

        else:
            latest_data = {
                "attack": "Normal",
                "can_id": str(cid),
                "time": ts,
                "ips_status": "ALLOW",
                "real_label": real,
                "ml_label": pred,
                "detection_time": det,
                "severity": "None"
            }

        # 🔥 TRAFFIC LOG
        traffic_log.append({
            "time": ts,
            "can_id": str(cid),
            "type": pred,
            "detection_time": det,
            "action": "BLOCKED" if pred != "Normal" else "ALLOW",
            "severity": sev(pred) if pred != "Normal" else "None"
        })

        if len(traffic_log) > 100:
            traffic_log.pop(0)

        counter["i"] += 1

    acc = round(stats["correct"] / max(stats["total"], 1) * 100, 1)

    return jsonify({
        **latest_data,
        **stats,
        "accuracy": acc,
        "running": system_running["status"]
    })

@app.route("/api/start", methods=["POST"])
@admin_only
def api_start():
    system_running["status"] = True
    return jsonify({"ok": True})

@app.route("/api/stop", methods=["POST"])
@admin_only
def api_stop():
    system_running["status"] = False
    return jsonify({"ok": True})

@app.route("/api/reset", methods=["POST"])
@admin_only
def api_reset():
    global attack_log, det_times, traffic_log
    stats.update(total=0, normal=0, dos=0, fuzzy=0, correct=0, blocked=0)
    attack_log, det_times, traffic_log = [], [], []
    return jsonify({"ok": True})

# ===== RUN =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)