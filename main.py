from fastapi import FastAPI, Request, HTTPException
from datetime import datetime
import pytz

app = FastAPI()

JOTFORM_SECRET = "515253"

@app.post("/jotform")
async def jotform_webhook(request: Request):
    data = await request.form()
    print("📦 DATA BRUTE JOTFORM :", data)
    return {"status": "received"}
