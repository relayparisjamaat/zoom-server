from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
import requests
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

app = FastAPI()

ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")
ZOOM_REDIRECT_URI = os.getenv("ZOOM_REDIRECT_URI")

TOKEN_FILE = "zoom_token.txt"


# ---------------------------
# UTILITAIRES
# ---------------------------
def save_token(token):
    with open(TOKEN_FILE, "w") as f:
        f.write(token)


def load_token():
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE) as f:
        return f.read()


# ---------------------------
# OAUTH – ÉTAPE 1
# ---------------------------
@app.get("/start")
def start_oauth():
    url = (
        "https://zoom.us/oauth/authorize"
        f"?response_type=code&client_id={ZOOM_CLIENT_ID}"
        f"&redirect_uri={ZOOM_REDIRECT_URI}"
    )
    return RedirectResponse(url)


# ---------------------------
# OAUTH – ÉTAPE 2
# ---------------------------
@app.get("/oauth/callback")
def oauth_callback(code: str):
    r = requests.post(
        "https://zoom.us/oauth/token",
        auth=(ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": ZOOM_REDIRECT_URI,
        },
    )
    r.raise_for_status()
    token = r.json()["access_token"]
    save_token(token)
    return {"status": "OAuth OK – token enregistré"}


# ---------------------------
# WEBHOOK JOTFORM
# ---------------------------
@app.post("/jotform")
async def jotform_webhook(request: Request):
    token = load_token()
    if not token:
        return RedirectResponse("/start")

    form = await request.form()
    raw = form.get("rawRequest")
    data = eval(raw)  # simplification volontaire

    if data.get("q14_codeSecret") != JOTFORM_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
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

    # ---------------------------
    # CRÉATION RÉUNION ZOOM
    # ---------------------------
    meeting_payload = {
        "topic": title,
        "type": 2,
        "start_time": start_time,
        "duration": duration,
        "schedule_for": email,
        "settings": {
            "auto_recording": "cloud" if recording else "none"
        }
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    r = requests.post(
        "https://api.zoom.us/v2/users/me/meetings",
        headers=headers,
        json=meeting_payload
    )
    r.raise_for_status()
    meeting = r.json()

    # ---------------------------
    # ENVOI MAIL
    # ---------------------------
    msg = MIMEText(
        f"""
Votre réunion Zoom a été créée.

Titre : {title}
Date : {start_time}
Lien Zoom : {meeting['join_url']}

Vous êtes l'hôte de la réunion.
"""
    )
    msg["Subject"] = "Votre réunion Zoom"
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
        server.send_message(msg)

    return {"status": "Réunion créée et mail envoyé"}

'''
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
import requests
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import pytz
import json
import secrets

app = FastAPI()
logging.basicConfig(level=logging.INFO)

PENDING = {}
ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")
ZOOM_REDIRECT_URI = os.getenv("ZOOM_REDIRECT_URI")
TOKEN_FILE = "zoom_token.txt"

# --- CONFIGURATION ---
CLIENT_ID = "NyfRXLUqT7aXqE2jiMrow"
CLIENT_SECRET = "kOzy09JN4BspXvzaDZSswNpY8koZMKds"
REDIRECT_URI = "https://zoom-server-zruq.onrender.com/zoom/callback"
JOTFORM_SECRET = "515253"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "relay.parisjamaat@gmail.com"          # ton email
SMTP_PASSWORD = "Relayparis53"         # mot de passe d'application Gmail
FROM_NAME = "Zoom Scheduler"

# ---------------------------
# UTILITAIRES
# ---------------------------
def save_token(token):
    with open(TOKEN_FILE, "w") as f:
        f.write(token)


def load_token():
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE) as f:
        return f.read()

# --- EMAIL ---
def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg['From'] = FROM_NAME
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SMTP_USER, SMTP_PASSWORD)
    server.send_message(msg)
    server.quit()
    logging.info(f"✅ Email envoyé à {to_email}")

# ---------------------------
# OAUTH – ÉTAPE 1
# ---------------------------
@app.get("/start")
def start_oauth(token: str):
    zoom_url = (
        "https://zoom.us/oauth/authorize"
        f"?response_type=code"
        f"&client_id={ZOOM_CLIENT_ID}"
        f"&redirect_uri={ZOOM_REDIRECT_URI}"
        f"&state={token}"
    )
    return RedirectResponse(zoom_url)

# ---------------------------
# OAUTH – ÉTAPE 2
# ---------------------------
@app.get("/oauth/callback")
def oauth_callback(code: str):
    r = requests.post(
        "https://zoom.us/oauth/token",
        auth=(ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": ZOOM_REDIRECT_URI,
        },
    )
    r.raise_for_status()
    token = r.json()["access_token"]
    save_token(token)
    return {"status": "OAuth OK – token enregistré"}
    
# --- JOTFORM WEBHOOK ---
@app.get("/")
def root():
    return {"message": "Server is running"}
    
# --- JOTFORM WEBHOOK ---
@app.post("/jotform")
async def jotform_webhook(request: Request):    
    form = await request.form()
    
    logging.info(f"📦 FORM KEYS REÇUES : {list(form.keys())}")

    raw = form.get("rawRequest")
    if not raw:
        logging.error("❌ rawRequest absent")
        raise HTTPException(status_code=400, detail="rawRequest manquant")

    try:
        parsed = json.loads(raw)
    except Exception as e:
        logging.error(f"❌ JSON invalide : {e}")
        raise HTTPException(status_code=400, detail="JSON invalide")

    # 🔍 LOG DU CONTENU PARSÉ
    logging.info(f"📦 PAYLOAD PARSÉ : {parsed}")
    
    if parsed.get("q14_codeSecret") != JOTFORM_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    # Extraction
    first_name = parsed.get("q9_first_name")
    last_name = parsed.get("q10_last_time")
    email = parsed.get("q11_eEmail")
    phone = parsed.get("q12_phone")
    session_type = parsed.get("q3_session_type")
    title = parsed.get("q4_title")
    description = parsed.get("q7_description")
    date = parsed.get("q15_date")
    time = parsed.get("q14_heure")
    duration_raw = parsed.get("q6_duration")
    recording = parsed.get("q13_recording")

    # --- REDIRECTION OAUTH ---
    token = secrets.token_urlsafe(32)
    PENDING[token] = parsed
    return {
        "status": "ok",
        "message": "Formulaire reçu",
        "auth_url": f"https://tonserveur.com/start?token={token}"
    }

# --- CALLBACK OAUTH ZOOM ---
@app.get("/zoom/callback")
def zoom_callback(code: str, state: str):
    # state contient l'email de l'utilisateur
    email = state

    # Échanger code contre access token
    token_url = "https://zoom.us/oauth/token"
    params = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    auth = (CLIENT_ID, CLIENT_SECRET)
    r = requests.post(token_url, params=params, auth=auth)
    r.raise_for_status()
    token_data = r.json()
    access_token = token_data["access_token"]

    # --- Récupérer l'user ID Zoom ---
    headers = {"Authorization": f"Bearer {access_token}"}
    r_user = requests.get("https://api.zoom.us/v2/users/me", headers=headers)
    r_user.raise_for_status()
    user_id = r_user.json()["id"]

    # --- Créer la réunion ---
    # Pour simplifier, ici on crée une réunion 30 min à partir de l'heure actuelle
    start_time = (datetime.utcnow() + timedelta(minutes=15)).replace(microsecond=0).isoformat() + "Z"
    payload = {
        "topic": "Réunion Test",
        "type": 2,
        "start_time": start_time,
        "duration": 30,
        "agenda": "Réunion créée via Jotform",
        "settings": {
            "host_video": True,
            "participant_video": True,
            "join_before_host": False,
            "auto_recording": "cloud"
        }
    }
    meeting_url = f"https://api.zoom.us/v2/users/{user_id}/meetings"
    r_meeting = requests.post(meeting_url, headers=headers, json=payload)
    r_meeting.raise_for_status()
    join_url = r_meeting.json()["join_url"]

    # --- Envoyer mail ---
    body = f"Votre réunion Zoom a été créée avec succès !\nLien : {join_url}"
    send_email(email, "Votre réunion Zoom", body)

    return {"status": "success", "join_url": join_url}
'''
