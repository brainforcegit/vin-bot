from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .database import init_db, SessionLocal, VINLog
import json

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
    print("📥 Получен запрос:", data)
    vin = data.vin.upper()

    if len(vin) != 17 or not vin.isalnum():
        raise HTTPException(status_code=400, detail="Invalid VIN")

    report = {
        "vin": vin,
        "model": "Hyundai Elantra 2014",
        "owners": 2,
        "mileage": "154,000 կմ",
        "accident": "Այո (2018 թ․ թեթև հետի հարված)",
        "imported": "ԱՄՆ-ից, 2020 թ․",
    }

    # Պահպանում ենք տվյալները
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
from typing import List

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
