from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import flats, owners, maintenance, payments, notices, auth

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SocietyPay API",
    description="Flat Management System — Sunrise Heights Society",
    version="1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Change origins to your actual frontend domain in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,        prefix="/api/auth",        tags=["Auth"])
app.include_router(flats.router,       prefix="/api/flats",       tags=["Flats"])
app.include_router(owners.router,      prefix="/api/owners",      tags=["Owners"])
app.include_router(maintenance.router, prefix="/api/maintenance", tags=["Maintenance"])
app.include_router(payments.router,    prefix="/api/payments",    tags=["Payments"])
app.include_router(notices.router,     prefix="/api/notices",     tags=["Notices"])


@app.get("/")
def root():
    return {"message": "SocietyPay API is running", "docs": "/docs"}
