from fastapi import FastAPI

app = FastAPI(title="Bitcor API")

@app.get("/healthz")
def healthz():
    return {"ok": True}
