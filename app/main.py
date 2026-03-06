from fastapi import FastAPI
from app.core.config import settings
from app.api.api import api_router
from app.db.database import engine, Base

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for mobile LAN access)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.1"}

app.include_router(api_router, prefix=settings.API_V1_STR)

# Serve React App (Production Build)
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Use absolute paths to avoid issues with CWD
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, "frontend-app", "dist")
ASSETS_DIR = os.path.join(DIST_DIR, "assets")

# Mount the static directory (CSS, JS, Assets)
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# Serve Index.html for root and unknown routes (SPA Support)
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    # Skip API routes
    if full_path.startswith("api"):
        return {"error": "API route not found"}
        
    index_path = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend build not found. Run 'npm run build' in frontend-app."}
