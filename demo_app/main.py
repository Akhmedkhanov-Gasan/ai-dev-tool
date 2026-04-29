from fastapi import FastAPI
from datetime import datetime, timezone

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/ping")
async def ping():
    return {'pong': True}

@app.get("/time")
async def get_current_time():
    current_time = datetime.now(timezone.utc)
    return {"current_time": current_time.isoformat()}

@app.get("/hello")
async def hello():
    return {"message": "hello"}

@app.get("/version")
async def version():
    return {"version": "1.0.0"}

@app.get("/status")
async def status():
    return {"service": "demo_app", "status": "running"}

@app.get("/build-info")
async def build_info():
    return {"name": "demo_app", "version": "1.0.0"}
