from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Import the new API router
from app.api.endpoints import router as api_router

# --- FastAPI App Initialization ---
app = FastAPI(title="Project Sentinel API")

# --- CORS Middleware ---
origins = [
    "http://localhost:3000",
    "https://project-sentinel-2.onrender.com",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include the API Routes ---
# This line adds all the endpoints from our endpoints.py file
app.include_router(api_router)

# --- Serve the React Frontend ---
# This must come AFTER your API routes.

# 1. Mount the 'static' folder from the React build
app.mount("/static", StaticFiles(directory="dashboard-ui/build/static"), name="static")

# 2. Create a catch-all route that serves the index.html for any other path
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    return FileResponse("dashboard-ui/build/index.html")

