from fastapi import FastAPI, Request, HTTPException
from datetime import datetime
import requests

#####################################################################################

ZOOM_JWT_TOKEN = "TON_TOKEN_JWT"

def create_zoom_user(email, first_name, last_name):
    url = "https://api.zoom.us/v2/users"
    headers = {
        "Authorization": f"Bearer {ZOOM_JWT_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "action": "create",
        "user_info": {
            "email": email,
            "type": 1,  # Basic
            "first_name": first_name,
            "last_name": last_name
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code in [201, 409]:  # 201 = créé, 409 = existe déjà
        data = response.json()
        return data
    else:
        raise Exception(f"Erreur Zoom : {response.status_code} {response.text}")

#####################################################################################

def create_zoom_session(host_id, session_type, topic, description, start_time, duration, recording_enabled):
    """
    Crée une réunion ou webinar Zoom pour un utilisateur existant.
    """
    url = f"https://api.zoom.us/v2/users/{host_id}/meetings"
    if session_type == "webinar":
        url = f"https://api.zoom.us/v2/users/{host_id}/webinars"

    headers = {
        "Authorization": f"Bearer {ZOOM_JWT_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "topic": topic,
        "type": 2,  # 2 = Scheduled meeting / webinar
        "start_time": start_time.isoformat(),  # ISO format avec timezone
        "duration": duration,  # en minutes
        "agenda": description,
        "settings": {
            "host_video": True,
            "participant_video": True,
            "join_before_host": False,
            "approval_type": 0,  # auto-approval
            "registration_type": 1,
            "meeting_authentication": False,
            "auto_recording": "cloud" if recording_enabled else "none"
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code in [201, 200]:
        return response.json()
    else:
        raise Exception(f"Erreur Zoom session : {response.status_code} {response.text}")

#####################################################################################

def get_upcoming_zoom_meetings(host_id):
    url = f"https://api.zoom.us/v2/users/{host_id}/meetings?type=scheduled"
    headers = {
        "Authorization": f"Bearer {ZOOM_JWT_TOKEN}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Erreur récupération meetings : {response.status_code} {response.text}")

    meetings = response.json().get("meetings", [])
    summary = []
    for m in meetings:
        start = m.get("start_time")  # ISO string
        topic = m.get("topic")
        duration = m.get("duration")
        summary.append(f"{topic} - {start} ({duration} min)")
    return summary

#####################################################################################

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

        # Créer ou récupérer l'utilisateur Zoom
        zoom_user = create_zoom_user(email, first_name, last_name)
        host_id = zoom_user.get("id")  # cet ID servira pour créer la réunion
        print("Zoom User créé ou existant :", host_id)

        # Créer la réunion ou webinar
        try:
            zoom_session = create_zoom_session(
                host_id=host_id,
                session_type=session_type,
                topic=title,
                description=description,
                start_time=start_datetime,
                duration=duration,
                recording_enabled=recording_enabled
            )
            join_url = zoom_session.get("join_url")
            conflict = False
        except Exception as e:
            if "409" in str(e):  # conflit horaire
                conflict = True
                join_url = None
                upcoming_meetings = get_upcoming_zoom_meetings(host_id)
            else:
                raise e

        print("Zoom session créée :", zoom_session.get("join_url"))
        
        except Exception as e:
            print("🔥 ERREUR :", str(e))
            raise HTTPException(status_code=500, detail="Erreur serveur interne")

        if conflict:
            body = "Impossible de créer la réunion, il y a un conflit. Voici vos réunions à venir :\n\n"
            body += "\n".join(upcoming_meetings)
        else:
            body = f"Votre réunion a été créée : {join_url}"
    
        return {"status": "received"}


