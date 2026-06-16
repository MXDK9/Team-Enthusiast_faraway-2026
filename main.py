import os
import asyncio
import json
import random
import math
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from agents import RailSenseAgentCoordinator
from anomaly_detector import StructuralVibrationEngine
detector = StructuralVibrationEngine()
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    if not firebase_admin._apps:
        # Mock credentials initialization since we don't have the user's private serviceAccountKey.json
        print("Firebase Admin SDK loaded. Running in local fallback mode (No credentials provided).")
        db = None
except ImportError:
    print("Firebase Admin SDK not installed. Running without Firebase.")
    db = None
except Exception as e:
    print(f"Firebase Init Error: {e}")
    db = None

# Load environment variables
backend_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(backend_dir, ".env")
load_dotenv(dotenv_path)

app = FastAPI(title="ZuupPad Infrastructure & Remote Sensing Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

railsense_manager = ConnectionManager()

railsense_coordinator = RailSenseAgentCoordinator()

# Global Agent Lock States
railsense_agent_active = False

# ─────────────────────────────────────────────────────────
#  RAILSENSE SIMULATION DATA
# ─────────────────────────────────────────────────────────
ROUTES = [
    {"id":"R01", "name":"Delhi → Mumbai", "short":"Western Trunk", "km":1384, "health":72, "color":"#ff7722"},
    {"id":"R02", "name":"Delhi → Kolkata", "short":"Grand Chord", "km":1446, "health":85, "color":"#ffd100"},
    {"id":"R03", "name":"Mumbai → Chennai", "short":"CR Main Line", "km":1278, "health":57, "color":"#ff2244"},
    {"id":"R04", "name":"Chennai → Kolkata", "short":"Coromandel Exp", "km":1662, "health":79, "color":"#bb55ff"},
    {"id":"R05", "name":"Delhi → Chennai", "short":"Grand Trunk Exp", "km":2194, "health":91, "color":"#00c8ff"},
    {"id":"R06", "name":"Delhi → Amritsar", "short":"Punjab Mail", "km":449, "health":94, "color":"#00ff88"},
    {"id":"R07", "name":"Delhi → Ahmedabad", "short":"Rajdhani Exp", "km":934, "health":88, "color":"#ffaa00"},
    {"id":"R08", "name":"Kolkata → Guwahati", "short":"NE Express", "km":1032, "health":76, "color":"#ff8844"},
    {"id":"R09", "name":"Mumbai → Bengaluru", "short":"UBL Trunk", "km":1214, "health":83, "color":"#ff9900"},
    {"id":"R10", "name":"Bengaluru ↔ Chennai", "short":"BNC-MAS Mail", "km":362, "health":96, "color":"#44ff88"},
    {"id":"R11", "name":"Bengaluru → Hyderabad", "short":"SC-YPR Exp", "km":574, "health":89, "color":"#cc55ff"},
    {"id":"R12", "name":"Hyderabad → Mumbai", "short":"Hussainsagar Exp", "km":711, "health":65, "color":"#ff4422"}
]

TRAIN_NAMES = [
  'Rajdhani Exp','Shatabdi Exp','Duronto Exp','Vande Bharat',
  'Garib Rath','Humsafar Exp','Tejas Exp','Intercity Exp',
  'Jan Shatabdi','Mail Express','Superfast Exp','Sampark Kranti',
  'Yuva Express','Kavi Guru Exp','Nanda Devi Exp','Gomti Exp',
  'Brahmaputra Exp','Deccan Exp','Gitanjali Exp','Konkan Kanya',
]
TRAIN_NOS = [12301,12302,12951,22221,12259,12463,22119,18407,12037,12431,12621,12651,12311,15959,14055,12531,15901,11007,12859,10101]

TRAINS = []
for ri, route in enumerate(ROUTES):
    n = 2 if route["km"] > 900 else 1
    for i in range(n):
        idx = len(TRAINS) % len(TRAIN_NAMES)
        t_val = 0.05 + random.random()*0.45 if i == 0 else 0.5 + random.random()*0.45
        TRAINS.append({
            "id": f"T{str(len(TRAINS)+1).zfill(2)}",
            "name": TRAIN_NAMES[idx],
            "no": TRAIN_NOS[idx],
            "route_id": route["id"],
            "t": t_val,
            "dir": 1 if i % 2 == 0 else -1,
            "speed": int(65 + random.random()*95),
            "vib": round(0.08 + random.random()*0.48, 2),
            "base_speed": int(65 + random.random()*95),
            "vib_history": [],
            "ai_anomaly_score": 0.0
        })

RAILSENSE_ALERTS = [
  {"t":'crit',"msg":'Ballast erosion 82% — KM 427, Delhi–Mumbai. Immediate inspection.',        "time":'2m ago'},
  {"t":'crit',"msg":'Lateral vibration anomaly at KM 892. Speed restriction active.',           "time":'5m ago'},
  {"t":'warn',"msg":'Rail temp 54°C — Chennai–Kolkata route. Thermal monitoring engaged.',      "time":'9m ago'},
  {"t":'crit',"msg":'Joint corrosion pattern — 3 consecutive anomalies, KM 1103.',             "time":'12m ago'},
  {"t":'warn',"msg":'Vibration spike 47Hz Express 12302. Wheel flat suspected.',               "time":'15m ago'},
  {"t":'warn',"msg":'Track gauge deviation +3.2mm at KM 256. Maintenance flagged.',            "time":'19m ago'},
]

def add_railsense_alert(alert_type: str, msg: str, time_label: str = "Just now"):
    alert = {"t": alert_type, "msg": msg, "time": time_label}
    RAILSENSE_ALERTS.insert(0, alert)
    if len(RAILSENSE_ALERTS) > 12:
        RAILSENSE_ALERTS.pop()
    
    # Mock Firebase push
    if db:
        try:
            db.collection("railsense_alerts").add(alert)
        except Exception:
            pass

# ─────────────────────────────────────────────────────────
#  AGENT TRIGGER IMPLEMENTATIONS
# ─────────────────────────────────────────────────────────
async def trigger_railsense_agent(train):
    global railsense_agent_active
    railsense_agent_active = True
    try:
        # Generate custom log message
        add_railsense_alert("warn", f"AI coordinator reviewing safety conditions on Train {train['id']}...", "Just now")
        
        # Format payload
        payload = [{
            "train_id": train["id"],
            "name": train["name"],
            "route_id": train["route_id"],
            "speed": train["speed"],
            "vib": train["vib"],
            "ai_anomaly_score": train["ai_anomaly_score"]
        }]
        
        thought, command = await railsense_coordinator.get_decision(payload)
        
        if thought:
            cleaned_thought = thought.replace("\n", " ")
            add_railsense_alert("info", f"[AGENT] Coordinator: {cleaned_thought[:85]}...", "Just now")
            
        if command and isinstance(command, dict):
            action = command.get("action")
            if action == "RestrictSpeed":
                train_id = command.get("train_id")
                speed = command.get("speed", 50)
                t_match = next((tr for tr in TRAINS if tr["id"] == train_id), None)
                if t_match:
                    t_match["base_speed"] = speed
                    t_match["speed"] = speed
                    add_railsense_alert("crit", f"LIMIT ENFORCED: Speed restricted to {speed}km/h for Train {train_id} (AI Anomaly Detected).", "Just now")
            elif action == "InspectTrack":
                route_id = command.get("route_id")
                add_railsense_alert("crit", f"INSPECTION: Dispatching safety crew to segment {route_id}.", "Just now")
            elif action == "SuggestMaintenanceSchedule":
                route_id = command.get("route_id")
                urgency = command.get("urgency", "High")
                add_railsense_alert("warn", f"AI MAINTENANCE: Scheduling {urgency} urgency maintenance for Route {route_id}.", "Just now")
            elif action == "PredictDerailmentRisk":
                train_id = command.get("train_id")
                risk = command.get("risk_level", "Medium")
                add_railsense_alert("crit" if risk=="High" else "warn", f"AI PREDICTION: Derailment risk for Train {train_id} is {risk}.", "Just now")
    except Exception as e:
        print(f"Error in RailSense agent evaluation: {e}")
    finally:
        railsense_agent_active = False

# ─────────────────────────────────────────────────────────
#  SIMULATION LOOPS
# ─────────────────────────────────────────────────────────
SPEED_SCALE = 0.00065

async def run_railsense_sim():
    print("Starting RailSense simulation feed...")
    tick = 0
    while True:
        tick += 1
        
        # Move trains
        for t in TRAINS:
            t["t"] += t["dir"] * SPEED_SCALE * (t["speed"] / 80.0)
            if t["t"] >= 0.98:
                t["t"] = 0.97
                t["dir"] = -1
            if t["t"] <= 0.02:
                t["t"] = 0.03
                t["dir"] = 1
                
            # Simulate slight speed adjustments
            t["speed"] = max(40, min(160, int(t["base_speed"] + random.randint(-4, 4))))
            
            # Vibration simulation
            route = next(r for r in ROUTES if r["id"] == t["route_id"])
            if route["health"] < 60:
                # critical track segment
                t["vib"] = round(0.32 + random.random()*0.42, 2)
            elif route["health"] < 80:
                t["vib"] = round(0.18 + random.random()*0.28, 2)
            else:
                t["vib"] = round(0.06 + random.random()*0.15, 2)
                
            # Random occasional vibration spikes (simulates anomalies)
            if random.random() < 0.03:
                t["vib"] = round(0.46 + random.random()*0.22, 2)
                
            # Maintain vibration history for TensorFlow model
            t["vib_history"].append(t["vib"])
            if len(t["vib_history"]) > 10:
                t["vib_history"].pop(0)
                
            # Predict Anomaly Score using Mathematical Model
            analysis = detector.analyze_vibration_window(t["vib_history"])
            t["ai_anomaly_score"] = analysis.get("rms_acceleration", 0.0)

        # Monitor anomalies and invoke agent coordinator
        anom_trains = [t for t in TRAINS if t["vib"] > 0.45 or t["ai_anomaly_score"] > 0.6]
        if anom_trains and not railsense_agent_active and tick % 45 == 0:
            asyncio.create_task(trigger_railsense_agent(anom_trains[0]))

        # Calculate network averages
        crit_segs = sum(1 for r in ROUTES if r["health"] < 60)
        warnings = sum(1 for r in ROUTES if 60 <= r["health"] < 80)
        healthy_segs = sum(1 for r in ROUTES if r["health"] >= 80)
        net_health = int(sum(r["health"] for r in ROUTES) / len(ROUTES))
        
        payload = {
            "type": "telemetry",
            "trains": [{
                "id": t["id"],
                "speed": t["speed"],
                "vib": t["vib"],
                "t": t["t"],
                "ai_anomaly_score": t["ai_anomaly_score"]
            } for t in TRAINS],
            "stats": {
                "live_trains": len(TRAINS),
                "crit_segs": crit_segs,
                "warnings": warnings,
                "healthy_segs": healthy_segs,
                "net_health": net_health
            },
            "alerts": RAILSENSE_ALERTS
        }
        
        await railsense_manager.broadcast(json.dumps(payload))
        await asyncio.sleep(1.0)

# ─────────────────────────────────────────────────────────
#  FASTAPI ROUTING & SOCKETS
# ─────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_railsense_sim())

@app.websocket("/ws/railsense")
async def websocket_railsense(websocket: WebSocket):
    await railsense_manager.connect(websocket)
    try:
        while True:
            # Keep socket alive and listen for client commands if any
            await websocket.receive_text()
    except WebSocketDisconnect:
        railsense_manager.disconnect(websocket)

# Flexible route to serve index.html from either flat root or subdirectories
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(dir_path, "index.html"),
        os.path.join(dir_path, "..", "frontend", "index.html"),
        os.path.join(dir_path, "frontend", "index.html")
    ]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return HTMLResponse(content=f.read())
            except Exception as e:
                print(f"Error reading index file at {path}: {e}")
    return HTMLResponse(content="<h1>RailSense Interface Not Found</h1><p>Please ensure index.html is in the repository root or frontend/ directory.</p>", status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5050)
