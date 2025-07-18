import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from fuzzywuzzy import process

# --- Database Setup ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./project_sentinel.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- ORM Models ---
# (Assuming your models are in app/models/entity.py, but including them here for a self-contained file)
class Entity(Base):
    __tablename__ = "entities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String)
    source = Column(String)
    aliases = relationship("Alias", back_populates="entity", cascade="all, delete-orphan")

class Alias(Base):
    __tablename__ = "aliases"
    id = Column(Integer, primary_key=True, index=True)
    alias_name = Column(String, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"))
    entity = relationship("Entity", back_populates="aliases")

# --- Pydantic Models ---
class ScreenRequest(BaseModel):
    entity_name: str

class MatchResult(BaseModel):
    entity_id: int
    name: str
    type: str | None = None
    source: str | None = None
    aliases: list[str] = []

class ScreenResponse(BaseModel):
    matches: list[MatchResult]

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

# --- API Endpoints ---
@app.post("/v1/screen", response_model=ScreenResponse)
def screen_entity(request: ScreenRequest):
    db = SessionLocal()
    try:
        # Your tiered search logic here...
        # This is a simplified version for demonstration
        entities = db.query(Entity).all()
        choices = {e.id: e.name for e in entities}
        
        fuzzy_matches = process.extractBests(request.entity_name, choices, score_cutoff=85, limit=10)
        
        match_ids = [match[2] for match in fuzzy_matches]
        
        final_results = db.query(Entity).filter(Entity.id.in_(match_ids)).all()

        response_matches = [
            MatchResult(
                entity_id=entity.id,
                name=entity.name,
                type=entity.type,
                source=entity.source,
                aliases=[alias.alias_name for alias in entity.aliases]
            ) for entity in final_results
        ]
        return ScreenResponse(matches=response_matches)
    finally:
        db.close()

@app.get("/v1/entity/{entity_id}")
def get_entity(entity_id: int):
    db = SessionLocal()
    try:
        entity = db.query(Entity).filter(Entity.id == entity_id).first()
        if entity:
            return {
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "source": entity.source,
                "aliases": [alias.alias_name for alias in entity.aliases]
            }
        return {"error": "Entity not found"}
    finally:
        db.close()

# --- THE DEFINITIVE FIX FOR SERVING THE REACT APP ---
# This must come AFTER your API routes.

# 1. Mount the 'static' folder from the React build
app.mount("/static", StaticFiles(directory="dashboard-ui/build/static"), name="static")

# 2. Create a catch-all route that serves the index.html
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    return FileResponse("dashboard-ui/build/index.html")

