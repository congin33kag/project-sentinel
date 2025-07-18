from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fuzzywuzzy import process
from typing import Optional, List
from app.db.session import SessionLocal
from app.models.entity import Entity, Alias
from pydantic import BaseModel

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

router = APIRouter()

# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/v1/screen", response_model=ScreenResponse)
def screen_entity(request: ScreenRequest, db: Session = Depends(get_db)):
    entities = db.query(Entity).all()
    choices = {e.id: e.name for e in entities if e.name}
    
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

@router.get("/v1/entity/{entity_id}")
def get_entity(entity_id: int, db: Session = Depends(get_db)):
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