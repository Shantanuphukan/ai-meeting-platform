from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import connect_to_mongo, close_mongo_connection
from app.api.routes import meetings, live, review, export
from app.services.assamese_asr import transcribe_assamese

app = FastAPI(title="AI Meeting Minutes Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_db():
    await close_mongo_connection()

app.include_router(meetings.router, prefix="/api/meetings", tags=["Meetings"])
app.include_router(review.router, prefix="/api/review", tags=["Review"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])
app.include_router(live.router, tags=["Live"])

@app.get("/")
async def root():
    return {"status": "ok", "service": "AI Meeting Minutes Platform"}

@app.post("/test-assamese")
async def test_assamese(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    text = transcribe_assamese(audio_bytes, filename=file.filename or "audio.wav")
    return {"text": text}