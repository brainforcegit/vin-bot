import json
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .database import init_db, SessionLocal, VINLog

init_db()

app = FastAPI()

class VINRequest(BaseModel):
    vin: str
    user_id: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/check-vin")
def check_vin(data: VINRequest):

    vin = data.vin.upper()

    if len(vin) != 17 or not vin.isalnum():
        raise HTTPException(status_code=400, detail="Invalid VIN")

    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json"

    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        decoded = res.json()

        fields = {item["Variable"]: item["Value"] for item in decoded["Results"] if item["Value"]}
        report = {
            "vin": vin,
            "make": fields.get("Make"),
            "model": fields.get("Model"),
            "year": fields.get("Model Year"),
            "vehicle_type": fields.get("Vehicle Type"),
            "plant_country": fields.get("Plant Country"),
            "body_class": fields.get("Body Class"),
        }

        # 🔸 Պահպանում ենք տվյալները բազայում
        db = SessionLocal()
        log = VINLog(
            vin=vin,
            user_id=data.user_id,
            report=json.dumps(report)
        )
        db.add(log)
        db.commit()
        db.close()

        return {"status": "ok", "report": report}

    except Exception as e:
        print("[API ERROR]", e)
        raise HTTPException(status_code=500, detail="Failed to fetch VIN data")

@app.get("/history/{user_id}")
def get_user_history(user_id: str):
    db = SessionLocal()
    logs = db.query(VINLog).filter(VINLog.user_id == user_id).order_by(VINLog.timestamp.desc()).limit(10).all()
    db.close()

    result = []
    for log in logs:
        result.append({
            "vin": log.vin,
            "timestamp": log.timestamp.isoformat(),
            "report": json.loads(log.report)
        })

    return {"user_id": user_id, "history": result}
