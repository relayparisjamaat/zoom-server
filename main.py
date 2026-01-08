from fastapi import FastAPI, Request, HTTPException
from datetime import datetime

app = FastAPI()

JOTFORM_SECRET = "515253"

@app.post("/jotform")
async def jotform_webhook(request: Request):
    try:
        data = await request.form()
        print("📦 DATA BRUTE :", data)

        # 🔐 Sécurité
        if data.get("secret") != JOTFORM_SECRET:
            raise HTTPException(status_code=401, detail="Unauthorized")

        # 📥 Extraction
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        phone = data.get("phone")
        session_type = data.get("session_type")
        title = data.get("title")
        description = data.get("description")
        date = data.get("date")
        time = data.get("time")
        duration_raw = data.get("duration")
        recording = data.get("recording", "Non")

        # ✅ Vérification champs obligatoires
        required = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "session_type": session_type,
            "title": title,
            "date": date,
            "time": time,
            "duration": duration_raw,
        }

        missing = [k for k, v in required.items() if not v]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Champs manquants : {', '.join(missing)}"
            )

        # 🔄 Conversions sûres
        duration = int(duration_raw)
        recording_enabled = recording == "Oui"
        session_type = session_type.lower()

        # 📅 Date + heure
        start_datetime = datetime.strptime(
            f"{date} {time}",
            "%Y-%m-%d %H:%M"
        )

        print("✅ DONNÉES NETTOYÉES")
        print(email, session_type, title)
        print(start_datetime, duration, recording_enabled)

        return {"status": "received"}

    except Exception as e:
        print("🔥 ERREUR :", str(e))
        raise HTTPException(status_code=500, detail="Erreur serveur interne")
