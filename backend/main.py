from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from routers import metrics, creative
from routers import auth, activity
import traceback

app = FastAPI(
    title="AdNova India — Ad Optimizer API",
    description="AI-powered Meta Ads optimizer for Indian D2C brands",
    version="1.0.0"
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Global Error Processing Request: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "traceback": traceback.format_exc()},
        headers={"Access-Control-Allow-Origin": "*"}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://adnova-bp4f.vercel.app",
        "https://adnova-bp4f-i9jd1ew6u-aany30s-projects.vercel.app",
        "*"  # FastAPI will allow wildcard if we set allow_credentials to false, but we have True. So let's add origins explicitly.
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "PATCH", "DELETE", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

app.include_router(metrics.router)
app.include_router(creative.router)
app.include_router(auth.router)
app.include_router(activity.router)


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

