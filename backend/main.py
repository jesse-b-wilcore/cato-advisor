from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import analysis, manual_intake, documents

app = FastAPI(
    title="cATO Advisor API",
    description="AI-powered ATO artifact impact detection and SIA generation",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router,       prefix="/api/analysis",  tags=["UC1 — Diff Analysis"])
app.include_router(manual_intake.router,  prefix="/api/intake",    tags=["UC2 — Manual Intake"])
app.include_router(documents.router,      prefix="/api/documents", tags=["UC3 — Document Generation"])


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
