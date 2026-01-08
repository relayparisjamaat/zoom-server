@app.post("/jotform")
async def jotform_webhook(request: Request):
    data = await request.form()
    print("📦 DATA BRUTE JOTFORM :", data)
    return {"status": "received"}
