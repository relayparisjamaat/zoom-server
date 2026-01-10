from fastapi import FastAPI, Request, HTTPException
import requests
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import json
from datetime import timezone

app = FastAPI()

# -------------------------
# CONFIG
# -------------------------
ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")
ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

JOTFORM_PASSWORD = "515253" #correspond à un champ caché dans le Jotform

# -------------------------
# ZOOM TOKEN (Server-to-Server OAuth)
# -------------------------
def get_zoom_token():
    url = "https://zoom.us/oauth/token"
    params = {
        "grant_type": "account_credentials",
        "account_id": ZOOM_ACCOUNT_ID
    }

    r = requests.post(
        url,
        params=params,
        auth=(ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET)
    )

    r.raise_for_status()
    return r.json()["access_token"]

# -------------------------
# Create a Zoom User
# -------------------------

def get_or_create_zoom_user(email, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 1. Vérifier si l'utilisateur existe
    r = requests.get(
        "https://api.zoom.us/v2/users",
        headers=headers,
        params={"email": email}
    )

    if r.status_code == 200 and r.json().get("users"):
        return email  # user existe déjà

    # 2. Créer un user Basic
    payload = {
        "action": "create",
        "user_info": {
            "email": email,
            "type": 1  # BASIC (gratuit)
        }
    }

    r = requests.post(
        "https://api.zoom.us/v2/users",
        headers=headers,
        json=payload
    )
    r.raise_for_status()

    return email
    
# -------------------------
# WEBHOOK JOTFORM
# -------------------------
@app.post("/jotform")
async def jotform_webhook(request: Request):
    try:
        form = await request.form()
        raw = form.get("rawRequest")

        if not raw:
            raise HTTPException(status_code=400, detail="rawRequest manquant")

        data = json.loads(raw) # Jotform envoie un JSON stringifié

        print("🔥 Réception des données ok")
        
        if data.get("q14_codeSecret") != JOTFORM_PASSWORD:
            raise HTTPException(status_code=401, detail="Unauthorized")

        print("🔥 Mot de passe ok")
        print("🔥 Début extraction des données")
        # Extraction
        first_name = data.get("q9_first_name")
        last_name = data.get("q10_last_time")
        email = data.get("q11_eEmail")
        phone = data.get("q12_phone")
        session_type = data.get("q3_session_type")
        title = data.get("q4_title")
        description = data.get("q7_description")
        date = data.get("q15_date")
        time = data.get("q14_heure")
        duration_raw = data.get("q6_duration")
        recording = data.get("q13_recording")
        print("🔥 Extraction ok")

        '''
        # -------------------------
        # EXTRACTION DES DONNÉES
        # -------------------------
        title = data["q4_title"]
        description = data["q7_description"]
        email = data["q11_email"]
        duration = int(data["q6_duration"])
        recording = data["q13_recording"] == "Oui"

        date = data["q15_date"]
        time = data["q16_heure"]'''

        '''start_time = datetime.strptime(
            f"{date['year']}-{date['month']}-{date['day']} "
            f"{time['hourSelect']}:{time['minuteSelect']}",
            "%Y-%m-%d %H:%M"
        ).isoformat()'''

        print("🔥 Conversion date heure")
        
        start_time = datetime.strptime(
            f"{date['year']}-{date['month']}-{date['day']} "
            f"{time['hourSelect']}:{time['minuteSelect']}",
            "%Y-%m-%d %H:%M"
        ).replace(tzinfo=timezone.utc).isoformat()

        print("🔥 Conversion date heure ok")
        print("🔥 Création token")
        
        # -------------------------
        # TOKEN ZOOM
        # -------------------------
        token = get_zoom_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        print("🔥 Création token ok")
        
        # S'assurer que l'utilisateur existe dans Zoom
        host_email = get_or_create_zoom_user(email, token)

        print("🔥 Création User ok")

        # -------------------------
        # CRÉATION RÉUNION
        # -------------------------
        try:
            payload = {
                "topic": title,
                "type": 2,
                "start_time": start_time,
                "duration": duration,
                "agenda": description,
                "settings": {
                    "alternative_hosts": host_email,
                    "auto_recording": "cloud" if recording else "none"
                }
            }
            print("🔥 Création Meeting ok")
        except Exception as e:
            print("Moving to not adding an alternative host : ", host_email)
            payload = {
                "topic": title,
                "type": 2,
                "start_time": start_time,
                "duration": duration,
                "agenda": description,
                "settings": {
                    "alternative_hosts": "",
                    "auto_recording": "cloud" if recording else "none"
                }
            }
            print("🔥 Création Meeting ok sans alternative host")
            
        r = requests.post(
            "https://api.zoom.us/v2/users/me/meetings",
            headers=headers,
            json=payload
        )
        r.raise_for_status()
        meeting = r.json()

        print("🔥 Publication meeting ok")

        # -------------------------
        # ENVOI EMAIL
        # -------------------------
        body = f"""
                    Votre visioconférence Zoom a été créée.
                    
                    Titre : {title}
                    Date : {start_time}
                    Durée : {duration} minutes
                    
                    Lien Zoom :
                    {meeting['join_url']}
                    
                    Vous êtes désigné comme co-hôte de la réunion.
                """

        msg = MIMEText(body)
        msg["Subject"] = "Votre réunion Zoom"
        msg["From"] = SMTP_USER
        msg["To"] = email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        print("🔥 Mail ok")
        
        return {
            "status": "OK",
            "meeting_id": meeting["id"],
            "join_url": meeting["join_url"]
        }
        
    except Exception as e:
        print("🔥 ERREUR :", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------
# ROUTE DE TEST
# -------------------------
@app.get("/")
def root():
    return {"status": "server running"}










