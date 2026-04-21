from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import health, auth, users, clients, sites, reports, files
from app.api import leads, service_items, invoices, quotes

app = FastAPI(
    title="Sterling Stormwater CRM",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(clients.router)
app.include_router(sites.router)
app.include_router(reports.router)
app.include_router(files.router)
app.include_router(leads.router)
app.include_router(service_items.router)
app.include_router(invoices.router)
app.include_router(quotes.router)
