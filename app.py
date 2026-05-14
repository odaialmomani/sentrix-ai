from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import datetime
import threading
import time as _time
import random as _random

app = Flask(__name__)
app.secret_key = "sentrix_ai_v2_2024"

USERS = {
    "admin":   {"password": "admin123",   "role": "Admin",   "name": "Admin User"},
    "analyst": {"password": "analyst123", "role": "Analyst", "name": "Security Analyst"},
    "viewer":  {"password": "viewer123",  "role": "Viewer",  "name": "Viewer"},
}

system_running = {"status": True}
latest_data = {
    "attack": "Normal", "can_id": "--", "time": "--:--:--",
    "ips_status": "Monitoring", "real_label": "-", "ml_label": "-",
    "detection_time": 0, "severity": "None"
}
stats = {"total": 0, "normal": 0, "dos": 0, "fuzzy": 0, "correct": 0, "blocked": 0}
attack_log = []
det_times  = []

def sev(t):
    return "Critical" if t == "DoS" else "High" if t == "Fuzzy" else "None"

def auth(f):
    from functools import wraps
    @wraps(f)
    def w(*a, **k):
        if "user" not in session: return redirect(url_for("login"))
        return f(*a, **k)
    return w

def admin_only(f):
    from functools import wraps
    @wraps(f)
    def w(*a, **k):
        if "user" not in session: return redirect(url_for("login"))
        if session.get("role") != "Admin": return "Access Denied", 403
        return f(*a, **k)
    return w

def ctx():
    return dict(user=session.get("name",""), role=session.get("role",""),
                running=system_running["status"], log_count=len(attack_log))

# ===== Smart Simulator =====
SAMPLES = [
    {"CAN_ID":"0x18f","label":"Normal","det":9.2},
    {"CAN_ID":"0x260","label":"Normal","det":8.7},
    {"CAN_ID":"0x2a0","label":"Normal","det":10.1},
    {"CAN_ID":"0x350","label":"Normal","det":9.5},
    {"CAN_ID":"0x18f","label":"Normal","det":8.3},
    {"CAN_ID":"0x0",  "label":"DoS",   "det":12.4},
    {"CAN_ID":"0x0",  "label":"DoS",   "det":11.8},
    {"CAN_ID":"0x304","label":"Fuzzy", "det":15.2},
    {"CAN_ID":"0x18f","label":"Normal","det":9.1},
    {"CAN_ID":"0x260","label":"Normal","det":8.9},
    {"CAN_ID":"0x0",  "label":"DoS",   "det":13.1},
    {"CAN_ID":"0x672","label":"Fuzzy", "det":16.3},
    {"CAN_ID":"0x2a0","label":"Normal","det":9.8},
    {"CAN_ID":"0x350","label":"Normal","det":10.2},
    {"CAN_ID":"0x519","label":"Fuzzy", "det":14.7},
    {"CAN_ID":"0x18f","label":"Normal","det":8.5},
    {"CAN_ID":"0x0",  "label":"DoS",   "det":12.9},
    {"CAN_ID":"0x260","label":"Normal","det":9.3},
    {"CAN_ID":"0x7ff","label":"Fuzzy", "det":17.1},
    {"CAN_ID":"0x2a0","label":"Normal","det":8.8},
]

def run_auto_ml():
    global latest_data, stats, attack_log, det_times
    i = 0
    while True:
        try:
            row  = SAMPLES[i % len(SAMPLES)]
            pred = row["label"]
            det  = round(row["det"] + _random.uniform(-1.5, 1.5), 1)
            cid  = row["CAN_ID"]
            ts   = datetime.datetime.now().strftime("%H:%M:%S")

            stats["total"] += 1
            det_times.append(det)

            if pred == "Normal":   stats["normal"]  += 1
            elif pred == "DoS":    stats["dos"]     += 1
            elif pred == "Fuzzy":  stats["fuzzy"]   += 1

            stats["correct"] += 1

            if pred != "Normal":
                stats["blocked"] += 1
                s = sev(pred)
                attack_log.append({
                    "time": ts, "type": pred, "can_id": cid,
                    "detection_time": det, "real": pred,
                    "severity": s, "action": "BLOCKED"
                })
                latest_data = {
                    "attack": "ATTACK: " + pred, "can_id": cid, "time": ts,
                    "ips_status": "BLOCKED", "real_label": pred, "ml_label": pred,
                    "detection_time": det, "severity": s
                }
                print(f"[{ts}] ATTACK: {pred} | {cid} | {det}ms")
            else:
                latest_data = {
                    "attack": "Normal", "can_id": cid, "time": ts,
                    "ips_status": "ALLOW", "real_label": pred, "ml_label": pred,
                    "detection_time": det, "severity": "None"
                }
                print(f"[{ts}] Normal | {cid} | {det}ms")

        except Exception as e:
            print(f"Simulator error: {e}")

        i += 1
        _time.sleep(2)

threading.Thread(target=run_auto_ml, daemon=True).start()
print("SENTRIX AI — Smart Simulator Active!")

# ===== Routes =====
@app.route("/", methods=["GET","POST"])
def login():
    error = ""
    if request.method == "POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","")
        if u in USERS and USERS[u]["password"] == p:
            session.update(user=u, role=USERS[u]["role"], name=USERS[u]["name"])
            return redirect(url_for("dashboard"))
        error = "Invalid credentials. Please try again."
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@auth
def dashboard():
    acc = round(stats["correct"] / max(stats["total"], 1) * 100, 1)
    return render_template("dashboard.html", **ctx(), stats=stats,
                           latest=latest_data, accuracy=acc)

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
    return render_template("analytics.html", **ctx(), stats=stats,
                           logs=attack_log, accuracy=acc, latest=latest_data)

@app.route("/admin")
@admin_only
def admin():
    return render_template("admin.html", **ctx(), stats=stats, users=USERS)

@app.route("/about")
@auth
def about():
    return render_template("about.html", **ctx())

# ===== API =====
@app.route("/api/status")
@auth
def api_status():
    acc = round(stats["correct"] / max(stats["total"], 1) * 100, 1)
    return jsonify({**latest_data, **stats, "accuracy": acc,
                    "running": system_running["status"]})

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
    global attack_log, det_times
    stats.update(total=0, normal=0, dos=0, fuzzy=0, correct=0, blocked=0)
    attack_log, det_times = [], []
    latest_data.update(attack="Normal", can_id="--", time="--:--:--",
                       ips_status="Monitoring", real_label="-", ml_label="-",
                       detection_time=0, severity="None")
    return jsonify({"ok": True})

@app.route("/api/simulate", methods=["POST"])
@admin_only
def api_simulate():
    t  = request.json.get("type", "DoS")
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    s  = sev(t)
    attack_log.append({"time": ts, "type": t, "can_id": "0x000",
                       "detection_time": 5, "real": t, "severity": s, "action": "BLOCKED"})
    if t == "DoS":     stats["dos"]   += 1
    elif t == "Fuzzy": stats["fuzzy"] += 1
    stats["total"] += 1
    stats["blocked"] += 1
    latest_data.update(attack="ATTACK: "+t, can_id="0x000", time=ts,
                       ips_status="BLOCKED", real_label=t, ml_label=t,
                       detection_time=5, severity=s)
    return jsonify({"ok": True})

@app.route("/api/update", methods=["POST"])
def api_update():
    global latest_data, stats, attack_log, det_times
    d   = request.json
    ml  = d.get("ml_pred", "Normal")
    rl  = d.get("real_label", "Normal")
    det = d.get("detection_time", 0)
    cid = d.get("can_id", "--")
    ts  = datetime.datetime.now().strftime("%H:%M:%S")
    stats["total"] += 1
    det_times.append(det)
    if ml == "Normal":  stats["normal"]  += 1
    elif ml == "DoS":   stats["dos"]     += 1
    elif ml == "Fuzzy": stats["fuzzy"]   += 1
    if ml == rl:        stats["correct"] += 1
    if ml != "Normal":
        stats["blocked"] += 1
        s = sev(ml)
        attack_log.append({"time": ts, "type": ml, "can_id": str(cid),
                           "detection_time": det, "real": rl, "severity": s, "action": "BLOCKED"})
        latest_data = {"attack": "ATTACK: "+ml, "can_id": str(cid), "time": ts,
                       "ips_status": "BLOCKED", "real_label": rl, "ml_label": ml,
                       "detection_time": det, "severity": s}
    else:
        latest_data = {"attack": "Normal", "can_id": str(cid), "time": ts,
                       "ips_status": "ALLOW", "real_label": rl, "ml_label": ml,
                       "detection_time": det, "severity": "None"}
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)