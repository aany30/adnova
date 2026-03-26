from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import metrics, creative

app = FastAPI(
    title="AdNova India — Ad Optimizer API",
    description="AI-powered Meta Ads optimizer for Indian D2C brands",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics.router)
app.include_router(creative.router)


@app.get("/")
async def root():
    return {
        "app": "AdNova India",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
