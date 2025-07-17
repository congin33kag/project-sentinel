"""
SQLAlchemy ORM models for the Project Sentinel database.

This module defines the database schema for entities, aliases, and sanctions
as specified in the PRD.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Entity(Base):
    """
    Represents a banned organization or individual entity.
    
    This is the main table that stores information about entities
    that appear on various sanctions lists.
    """
    __tablename__ = 'entities'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False, index=True)
    type = Column(String(100), nullable=False, index=True)  # e.g., 'terrorist', 'unlawful', 'individual'
    
    # Optional fields for additional metadata
    description = Column(Text, nullable=True)
    source = Column(String(200), nullable=True)  # e.g., 'MHA', 'UN', 'OFAC'
    date_added = Column(DateTime, default=datetime.utcnow)
    date_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    aliases = relationship("Alias", back_populates="entity", cascade="all, delete-orphan")
    sanctions = relationship("Sanction", back_populates="entity", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Entity(id={self.id}, name='{self.name}', type='{self.type}')>"
    
    def __str__(self):
        return f"{self.name} ({self.type})"


class Alias(Base):
    """
    Represents alternative names or aliases for entities.
    
    This table stores all known aliases, alternate spellings, and
    alternative names for entities in the main entities table.
    """
    __tablename__ = 'aliases'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alias_name = Column(String(500), nullable=False, index=True)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    
    # Optional fields for alias metadata
    alias_type = Column(String(100), nullable=True)  # e.g., 'acronym', 'translation', 'alternate_spelling'
    source = Column(String(200), nullable=True)  # Where this alias was found
    date_added = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    entity = relationship("Entity", back_populates="aliases")
    
    def __repr__(self):
        return f"<Alias(id={self.id}, alias_name='{self.alias_name}', entity_id={self.entity_id})>"
    
    def __str__(self):
        return self.alias_name


class Sanction(Base):
    """
    Represents sanctions applied to entities.
    
    This table stores information about specific sanctions, including
    the sanctioning body, program, and other relevant details.
    """
    __tablename__ = 'sanctions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sanctioning_body = Column(String(200), nullable=False, index=True)  # e.g., 'MHA', 'UN Security Council', 'US Treasury'
    program = Column(String(300), nullable=False, index=True)  # e.g., 'Counter-Terrorism', 'OFAC SDN List'
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    
    # Optional fields for sanction details
    sanction_type = Column(String(100), nullable=True)  # e.g., 'asset_freeze', 'travel_ban', 'arms_embargo'
    reference_number = Column(String(100), nullable=True)  # Official reference or case number
    date_imposed = Column(DateTime, nullable=True)
    date_expires = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    legal_basis = Column(String(500), nullable=True)  # Legal framework or act under which sanction was imposed
    
    # Metadata
    date_added = Column(DateTime, default=datetime.utcnow)
    date_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    entity = relationship("Entity", back_populates="sanctions")
    
    def __repr__(self):
        return f"<Sanction(id={self.id}, sanctioning_body='{self.sanctioning_body}', program='{self.program}', entity_id={self.entity_id})>"
    
    def __str__(self):
        return f"{self.sanctioning_body} - {self.program}"


class Relationship(Base):
    __tablename__ = 'relationships'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    from_entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    to_entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    relation_type = Column(String(100), nullable=False)
    date_added = Column(DateTime, default=datetime.utcnow)
    
    from_entity = relationship("Entity", foreign_keys=[from_entity_id], backref="outgoing_relationships")
    to_entity = relationship("Entity", foreign_keys=[to_entity_id], backref="incoming_relationships")
    
    def __repr__(self):
        return f"<Relationship(id={self.id}, from={self.from_entity_id}, to={self.to_entity_id}, type='{self.relation_type}')>"


# Helper functions for common database operations
def create_entity_with_aliases(name, entity_type, aliases_list, source=None):
    """
    Helper function to create an entity with its aliases in a single operation.
    
    Args:
        name (str): Primary name of the entity
        entity_type (str): Type of entity (e.g., 'terrorist', 'unlawful')
        aliases_list (list): List of alias names
        source (str, optional): Source of the data
    
    Returns:
        Entity: The created entity object with aliases
    """
    entity = Entity(
        name=name,
        type=entity_type,
        source=source
    )
    
    # Add aliases
    for alias_name in aliases_list:
        if alias_name != name:  # Don't add the primary name as an alias
            alias = Alias(alias_name=alias_name, entity=entity)
            entity.aliases.append(alias)
    
    return entity


def create_sanction_entry(entity, sanctioning_body, program, **kwargs):
    """
    Helper function to create a sanction entry for an entity.
    
    Args:
        entity (Entity): The entity to which the sanction applies
        sanctioning_body (str): The body imposing the sanction
        program (str): The sanctions program
        **kwargs: Additional sanction details
    
    Returns:
        Sanction: The created sanction object
    """
    sanction = Sanction(
        entity=entity,
        sanctioning_body=sanctioning_body,
        program=program,
        **kwargs
    )
    
    return sanction 