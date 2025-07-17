"""
Project Sentinel - FastAPI Application

This is the main FastAPI application that provides endpoints for entity screening
against sanctions lists and banned organizations.
"""

from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy import create_engine, or_, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from thefuzz import fuzz

# Import our database models
from app.models.entity import Base, Entity, Alias, Sanction

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./project_sentinel.db')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create FastAPI app instance
app = FastAPI(
    title="Project Sentinel API",
    description="Entity screening API for sanctions lists and banned organizations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# New CORS configuration for React dev server
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve React static files
app.mount("/", StaticFiles(directory="dashboard-ui/build", html=True), name="static")

# Existing CORS (if any) below can be removed or kept as needed

# Database dependency
def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models for request/response validation
class ScreenRequest(BaseModel):
    """Request model for entity screening."""
    entity_name: str = Field(..., description="Name of the entity to screen", example="Al-Qaeda")
    country: Optional[str] = Field(None, description="Optional country filter", example="Pakistan")

class MatchResult(BaseModel):
    """Individual match result."""
    entity_id: int = Field(..., description="Unique identifier for the matched entity")
    name: str = Field(..., description="Primary name of the matched entity")
    type: str = Field(..., description="Type of entity (e.g., 'terrorist', 'unlawful')")
    aliases: List[str] = Field(default=[], description="List of known aliases")
    source: str = Field(..., description="Original data source of the entity (e.g., 'MHA India', 'US OFAC')")
    sanctioning_body: str = Field(..., description="Organization that imposed the sanction")
    program: str = Field(..., description="Sanctions program name")
    confidence_score: float = Field(..., description="Match confidence score (0.0 to 1.0)")
    last_updated: str = Field(..., description="Last update timestamp")

class ScreenResponse(BaseModel):
    """Response model for entity screening."""
    query: str = Field(..., description="Original query string")
    country_filter: Optional[str] = Field(None, description="Applied country filter")
    total_matches: int = Field(..., description="Total number of matches found")
    matches: List[MatchResult] = Field(default=[], description="List of matching entities")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    timestamp: str = Field(..., description="Response timestamp")

# Helper functions
def calculate_confidence_score(query: str, entity_name: str, matched_via_alias: bool = False) -> float:
    """
    Calculate confidence score based on match quality.
    
    Args:
        query: Original search query
        entity_name: Matched entity name
        matched_via_alias: Whether match was found via alias
        
    Returns:
        Confidence score between 0.0 and 1.0
    """
    query_lower = query.lower().strip()
    entity_lower = entity_name.lower().strip()
    
    # Exact match gets highest score
    if query_lower == entity_lower:
        return 0.95 if not matched_via_alias else 0.90
    
    # Check if query is contained in entity name or vice versa
    if query_lower in entity_lower:
        # Longer matches get higher scores
        ratio = len(query_lower) / len(entity_lower)
        base_score = 0.7 + (ratio * 0.2)
        return base_score if not matched_via_alias else base_score - 0.1
    
    if entity_lower in query_lower:
        ratio = len(entity_lower) / len(query_lower)
        base_score = 0.6 + (ratio * 0.2)
        return base_score if not matched_via_alias else base_score - 0.1
    
    # Partial match (this shouldn't happen with our current query logic, but just in case)
    return 0.5 if not matched_via_alias else 0.4

def search_entities(db: Session, query: str) -> List[Entity]:
    """
    Search for entities by name or alias with case-insensitive partial matching.
    
    Args:
        db: Database session
        query: Search query string
        
    Returns:
        List of matching Entity objects
    """
    try:
        # Create case-insensitive partial match pattern
        search_pattern = f"%{query.strip()}%"
        
        # Search in both entities and aliases tables
        # We use a subquery to find entity IDs that match either directly or via aliases
        entity_matches = db.query(Entity).filter(
            Entity.name.ilike(search_pattern)
        ).all()
        
        # Find entities that match via aliases
        alias_matches = db.query(Entity).join(Alias).filter(
            Alias.alias_name.ilike(search_pattern)
        ).all()
        
        # Combine and deduplicate results
        all_matches = entity_matches + alias_matches
        unique_matches = []
        seen_ids = set()
        
        for entity in all_matches:
            if entity.id not in seen_ids:
                unique_matches.append(entity)
                seen_ids.add(entity.id)
        
        return unique_matches
        
    except SQLAlchemyError as e:
        print(f"Database error during search: {e}")
        return []

# API Endpoints
@app.get("/")
async def root():
    """Serve the main index.html file."""
    return FileResponse("index.html", media_type="text/html")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/v1/screen", response_model=ScreenResponse)
async def screen_entity(request: ScreenRequest, db: Session = Depends(get_db)):
    """
    Screen an entity against sanctions lists and banned organizations.
    
    This endpoint accepts an entity name and optional country filter,
    then searches through the database of sanctioned entities to find matches.
    
    Args:
        request: ScreenRequest containing entity_name and optional country
        db: Database session (injected)
        
    Returns:
        ScreenResponse with matching entities and metadata
    """
    processing_start = datetime.utcnow()
    try:
        query = request.entity_name.strip()
        query_lower = query.lower()
        # Exact match on entity names (case-insensitive)
        exact_entity_matches = db.query(Entity).filter(func.lower(Entity.name) == query_lower).all()
        # Exact match on aliases (case-insensitive)
        exact_alias_matches = db.query(Entity).join(Alias).filter(func.lower(Alias.alias_name) == query_lower).all()
        # Fuzzy matches on entity names
        all_entities = db.query(Entity).all()
        fuzzy_matches = [e for e in all_entities if fuzz.ratio(query_lower, e.name.lower()) > 85]
        # Combine all matches, removing duplicates
        all_matches = set(exact_entity_matches + exact_alias_matches + fuzzy_matches)
        # Prepare match results with confidence scores
        matches = []
        for entity in all_matches:
            aliases = [alias.alias_name for alias in entity.aliases]
            sanction = entity.sanctions[0] if entity.sanctions else None
            sanctioning_body = sanction.sanctioning_body if sanction else "Unknown"
            program = sanction.program if sanction else "Unknown"
            # Determine confidence
            if entity in exact_alias_matches:
                confidence = 1.0
            elif entity in exact_entity_matches:
                confidence = 0.95
            else:
                confidence = fuzz.ratio(query_lower, entity.name.lower()) / 100.0
            match_result = MatchResult(
                entity_id=entity.id,
                name=entity.name,
                type=entity.type,
                aliases=aliases,
                source=entity.source or "Unknown",
                sanctioning_body=sanctioning_body,
                program=program,
                confidence_score=confidence,
                last_updated=entity.date_updated.isoformat() if entity.date_updated else datetime.utcnow().isoformat()
            )
            matches.append(match_result)
        # Sort by confidence descending
        matches.sort(key=lambda x: x.confidence_score, reverse=True)
        processing_end = datetime.utcnow()
        processing_time_ms = int((processing_end - processing_start).total_seconds() * 1000)
        response = ScreenResponse(
            query=request.entity_name,
            country_filter=request.country,
            total_matches=len(matches),
            matches=matches,
            processing_time_ms=processing_time_ms,
            timestamp=datetime.utcnow().isoformat()
        )
        return response
    except Exception as e:
        print(f"Error during entity screening: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during screening")

@app.get("/v1/stats")
async def get_statistics(db: Session = Depends(get_db)):
    """
    Get statistics about the sanctions database.
    
    Returns basic statistics about the number of entities, aliases, and sanctions
    in the database.
    """
    try:
        # Get actual database statistics
        total_entities = db.query(Entity).count()
        total_aliases = db.query(Alias).count()
        total_sanctions = db.query(Sanction).count()
        
        # Get entity type breakdown
        entity_types = {}
        for entity_type, count in db.query(Entity.type, db.func.count(Entity.id)).group_by(Entity.type).all():
            entity_types[entity_type] = count
        
        # Get source breakdown
        sources = {}
        for source, count in db.query(Entity.source, db.func.count(Entity.id)).group_by(Entity.source).all():
            sources[source or "Unknown"] = count
        
        return {
            "database_stats": {
                "total_entities": total_entities,
                "total_aliases": total_aliases,
                "total_sanctions": total_sanctions,
                "last_updated": datetime.utcnow().isoformat()
            },
            "sources": sources,
            "entity_types": entity_types
        }
        
    except SQLAlchemyError as e:
        print(f"Database error getting statistics: {e}")
        return {
            "database_stats": {
                "total_entities": 0,
                "total_aliases": 0,
                "total_sanctions": 0,
                "last_updated": datetime.utcnow().isoformat()
            },
            "sources": {},
            "entity_types": {}
        }

@app.get("/v1/entity/{entity_id}")
async def get_entity_details(entity_id: int, db: Session = Depends(get_db)):
    try:
        entity = db.query(Entity).filter(Entity.id == entity_id).first()
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        aliases = [alias.alias_name for alias in entity.aliases]
        return {
            "id": entity.id,
            "name": entity.name,
            "type": entity.type,
            "source": entity.source,
            "aliases": aliases
        }
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

# FIX: Error handlers now return proper JSONResponse objects
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An internal server error occurred",
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
