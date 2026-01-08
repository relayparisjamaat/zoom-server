from fastapi import FastAPI, Request, HTTPException
from datetime import datetime
import pytz

app = FastAPI()

JOTFORM_SECRET = "JOTFORM_SECRET_2026"

@app.post("/jotform")
