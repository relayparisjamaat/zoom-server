from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

JOTFORM_SECRET = "515253"

@app.get("/")
def root():
    return {"status": "server running"}

@app.get("/jotform")
def jotform_test():
    return {"status": "jotform endpoint ready"}

@app.post("/jotform")
async def jotform_webhook(request: Request):
    data = await request.form()

    # 🔐 Vérification du secret
    if data.get("secret") != JOTFORM_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    print("✅ Webhook sécurisé reçu :", data)
    return {"status": "received"}
