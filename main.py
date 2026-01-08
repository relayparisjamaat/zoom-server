from fastapi import FastAPI, Request

app = FastAPI()

@app.get("/")
def root():
    return {"status": "server running"}

@app.get("/jotform")
def jotform_test():
    return {"status": "jotform endpoint ready"}

@app.post("/jotform")
async def jotform_webhook(request: Request):
    data = await request.form()
    print(data)
    return {"status": "received"}
