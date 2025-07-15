#!/usr/bin/env python3
"""
Data Ingestion Script for Project Sentinel

This script reads the MHA banned organizations data from JSON and ingests it
into the SQLite database, creating Entity and Alias records.
"""

import json
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Add the parent directory to the path so we can import our models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.entity import Base, Entity, Alias, Sanction

class DataIngester:
    """Handles ingestion of data from multiple sources into the database."""
    
    def __init__(self, db_url="sqlite:///./project_sentinel.db"):
        """
        Initialize the data ingester.
        
        Args:
            db_url: Database connection URL
        """
        self.db_url = db_url
        self.engine = None
        self.Session = None
        self.session = None
        self.data_sources = ['mha_banned_list.json', 'ofac_sdn_list.json']
        
    def connect_to_database(self):
        """Establish connection to the database."""
        try:
            print(f"Connecting to database: {self.db_url}")
            self.engine = create_engine(self.db_url)
            
            # Create tables if they don't exist
            Base.metadata.create_all(self.engine)
            
            # Create session factory
            self.Session = sessionmaker(bind=self.engine)
            self.session = self.Session()
            
            print("Database connection established successfully.")
            return True
            
        except SQLAlchemyError as e:
            print(f"Error connecting to database: {e}")
            return False
    
    def load_json_data(self):
        """Load organization data from all JSON sources."""
        all_organizations = []
        
        for json_file in self.data_sources:
            print(f"Loading data from: {json_file}")
            
            if not os.path.exists(json_file):
                print(f"Warning: JSON file '{json_file}' not found. Skipping.")
                continue
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Handle both direct list and metadata wrapper formats
                if isinstance(data, dict) and 'organizations' in data:
                    organizations = data['organizations']
                elif isinstance(data, list):
                    organizations = data
                else:
                    print(f"Error: Unexpected JSON format in {json_file}")
                    continue
                
                all_organizations.extend(organizations)
                print(f"Loaded {len(organizations)} organizations from {json_file}")
                
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON file {json_file}: {e}")
            except Exception as e:
                print(f"Error loading JSON file {json_file}: {e}")
        
        print(f"\nTotal organizations loaded: {len(all_organizations)}")
        return all_organizations
    
    def entity_exists(self, name):
        """
        Check if an entity with the given name already exists in the database.
        
        Args:
            name: Entity name to check
            
        Returns:
            Entity object if exists, None otherwise
        """
        try:
            existing_entity = self.session.query(Entity).filter(
                Entity.name.ilike(name.strip())
            ).first()
            return existing_entity
        except SQLAlchemyError as e:
            print(f"Error checking if entity exists: {e}")
            return None
    
    def add_aliases(self, entity, aliases_list, source):
        """Delete existing aliases and add new ones for an entity."""
        try:
            # Delete existing aliases
            deleted = self.session.query(Alias).filter(Alias.entity_id == entity.id).delete()
            print(f"  Deleted {deleted} existing aliases")
            
            # Add new aliases
            aliases_created = 0
            for alias_name in aliases_list:
                alias_name = alias_name.strip()
                if alias_name and alias_name != entity.name:
                    alias = Alias(
                        alias_name=alias_name,
                        entity_id=entity.id,
                        source=source,
                        date_added=datetime.utcnow()
                    )
                    self.session.add(alias)
                    aliases_created += 1
            
            print(f"  Created {aliases_created} new aliases")
            return aliases_created
        except SQLAlchemyError as e:
            print(f"Error updating aliases: {e}")
            self.session.rollback()
            return 0
    
    def create_sanction(self, entity, category):
        """Create a sanction record for an entity."""
        try:
            sanction = Sanction(
                entity_id=entity.id,
                sanctioning_body='MHA India',
                program='Counter-Terrorism and Counter-Radicalization Division',
                sanction_type='Banned Organization',
                description=f'Listed as {category} organization',
                date_imposed=datetime.utcnow(),
                date_added=datetime.utcnow(),
                date_updated=datetime.utcnow()
            )
            self.session.add(sanction)
            print("  Created 1 sanction record")
            return 1
        except SQLAlchemyError as e:
            print(f"Error creating sanction: {e}")
            self.session.rollback()
            return 0
    
    def create_entity_with_aliases(self, org_data):
        """
        Create a new entity with its aliases and sanction information.
        
        Args:
            org_data: Dictionary containing organization data
            
        Returns:
            Created Entity object or None if failed
        """
        try:
            # Extract data from organization record
            primary_name = org_data.get('name', '').strip()
            aliases = org_data.get('aliases', [])
            category = org_data.get('category', 'unknown')
            source = org_data.get('source', 'MHA India')
            source_pdf = org_data.get('source_pdf', '')
            
            if not primary_name:
                print("Warning: Skipping organization with empty name")
                return None
            
            # Create the entity
            entity = Entity(
                name=primary_name,
                type=category,
                source=source,
                description=f"Imported from {source_pdf}" if source_pdf else None,
                date_added=datetime.utcnow(),
                date_updated=datetime.utcnow()
            )
            
            self.session.add(entity)
            self.session.flush()  # Get the entity ID
            
            # Add aliases
            aliases_created = self.add_aliases(entity, aliases, source)
            
            # Create sanction
            sanctions_created = self.create_sanction(entity, category)
            
            return entity, aliases_created, sanctions_created
            
        except SQLAlchemyError as e:
            print(f"Error creating entity: {e}")
            self.session.rollback()
            return None, 0, 0
    
    def update_existing_entity(self, entity, org_data):
        """
        Update an existing entity with new aliases.
        
        Args:
            entity: Existing Entity object
            org_data: Dictionary containing updated data
            
        Returns:
            Updated Entity object, aliases created count
        """
        try:
            # Extract data
            aliases = org_data.get('aliases', [])
            source = org_data.get('source', 'MHA India')
            
            # Update entity metadata if needed
            entity.date_updated = datetime.utcnow()
            self.session.add(entity)
            
            # Update aliases
            aliases_created = self.add_aliases(entity, aliases, source)
            
            return entity, aliases_created
            
        except SQLAlchemyError as e:
            print(f"Error updating entity: {e}")
            self.session.rollback()
            return None, 0
    
    def ingest_organizations(self, organizations):
        """
        Ingest all organizations from the loaded data.
        
        Args:
            organizations: List of organization dictionaries
            
        Returns:
            Dictionary with ingestion statistics
        """
        stats = {
            'total_processed': 0,
            'entities_created': 0,
            'entities_updated': 0,
            'entities_skipped': 0,
            'aliases_created': 0,
            'sanctions_created': 0,
            'errors': 0
        }
        
        print(f"\nStarting ingestion of {len(organizations)} organizations...")
        print("-" * 60)
        
        for i, org_data in enumerate(organizations, 1):
            try:
                primary_name = org_data.get('name', '').strip()
                
                if not primary_name:
                    print(f"[{i}/{len(organizations)}] Skipping organization with empty name")
                    stats['entities_skipped'] += 1
                    continue
                
                print(f"[{i}/{len(organizations)}] Ingesting '{primary_name}'...")
                
                # Check if entity already exists
                existing_entity = self.entity_exists(primary_name)
                
                if existing_entity:
                    print(f"Updating aliases for existing entity: {primary_name} (ID: {existing_entity.id})")
                    updated_entity, aliases_created = self.update_existing_entity(existing_entity, org_data)
                    
                    if updated_entity:
                        stats['entities_updated'] += 1
                        stats['aliases_created'] += aliases_created
                        self.session.commit()
                        print(f"  Successfully updated entity (ID: {updated_entity.id})")
                    else:
                        stats['errors'] += 1
                        print(f"  Failed to update entity")
                else:
                    # Create new entity with aliases and sanction
                    new_entity, aliases_created, sanctions_created = self.create_entity_with_aliases(org_data)
                    
                    if new_entity:
                        stats['entities_created'] += 1
                        stats['aliases_created'] += aliases_created
                        stats['sanctions_created'] += sanctions_created
                        self.session.commit()
                        print(f"  Successfully created entity (ID: {new_entity.id})")
                    else:
                        stats['errors'] += 1
                        print(f"  Failed to create entity")
                
                stats['total_processed'] += 1
                
                # Progress indicator for large datasets
                if i % 50 == 0:
                    print(f"\nProgress: {i}/{len(organizations)} organizations processed")
                    print(f"Created: {stats['entities_created']}, Updated: {stats['entities_updated']}, Skipped: {stats['entities_skipped']}, Errors: {stats['errors']}")
                    print("-" * 60)
                
            except Exception as e:
                print(f"[{i}/{len(organizations)}] Error processing organization: {e}")
                stats['errors'] += 1
                self.session.rollback()
        
        return stats
    
    def print_final_stats(self, stats):
        """Print final ingestion statistics."""
        print("\n" + "=" * 60)
        print("INGESTION COMPLETED")
        print("=" * 60)
        print(f"Total organizations processed: {stats['total_processed']}")
        print(f"Entities created: {stats['entities_created']}")
        print(f"Entities updated: {stats['entities_updated']}")
        print(f"Entities skipped (already exist): {stats['entities_skipped']}")
        print(f"Aliases created: {stats['aliases_created']}")
        print(f"Sanctions created: {stats['sanctions_created']}")
        print(f"Errors encountered: {stats['errors']}")
        print("=" * 60)
    
    def run(self):
        """Main execution method."""
        print("Starting MHA Banned Organizations Data Ingestion")
        print("=" * 60)
        
        # Connect to database
        if not self.connect_to_database():
            print("Failed to connect to database. Exiting.")
            return False
        
        try:
            # Load JSON data
            organizations = self.load_json_data()
            if not organizations:
                print("Failed to load organization data. Exiting.")
                return False
            
            # Ingest organizations
            stats = self.ingest_organizations(organizations)
            
            # Print final statistics
            self.print_final_stats(stats)
            
            print("\nFinished ingesting data.")
            return True
            
        except Exception as e:
            print(f"Unexpected error during ingestion: {e}")
            return False
        
        finally:
            # Close database connection
            if self.session:
                self.session.close()
            if self.engine:
                self.engine.dispose()
            print("Database connection closed.")

def main():
    """Main entry point."""
    # Create and run ingester
    ingester = DataIngester()
    success = ingester.run()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 