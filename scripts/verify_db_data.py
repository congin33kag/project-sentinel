#!/usr/bin/env python3
"""
Database Verification Script for Project Sentinel

This script connects to the project_sentinel.db database and verifies
the data by listing all entities and their counts.
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Add the parent directory to the path so we can import our models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.entity import Base, Entity, Alias, Sanction

class DatabaseVerifier:
    """Handles verification of database data."""
    
    def __init__(self, db_url="sqlite:///./project_sentinel.db"):
        """
        Initialize the database verifier.
        
        Args:
            db_url: Database connection URL
        """
        self.db_url = db_url
        self.engine = None
        self.Session = None
        self.session = None
        
    def connect_to_database(self):
        """Establish connection to the database."""
        try:
            print(f"Connecting to database: {self.db_url}")
            self.engine = create_engine(self.db_url)
            
            # Create session factory
            self.Session = sessionmaker(bind=self.engine)
            self.session = self.Session()
            
            print("Database connection established successfully.")
            return True
            
        except SQLAlchemyError as e:
            print(f"Error connecting to database: {e}")
            return False
    
    def verify_entities(self):
        """
        Query the Entities table and print all entity names.
        
        Returns:
            Number of entities found
        """
        try:
            print("\n" + "=" * 60)
            print("QUERYING ENTITIES TABLE")
            print("=" * 60)
            
            # Query all entities from the database
            entities = self.session.query(Entity).all()
            
            if not entities:
                print("No entities found in the database.")
                return 0
            
            print(f"Found {len(entities)} entities in the database:\n")
            
            # Print each entity with details
            for i, entity in enumerate(entities, 1):
                print(f"{i:3d}. {entity.name}")
                print(f"     Type: {entity.type}")
                print(f"     Source: {entity.source or 'Unknown'}")
                print(f"     Aliases: {len(entity.aliases)} alias(es)")
                print(f"     Sanctions: {len(entity.sanctions)} sanction(s)")
                print(f"     Date Added: {entity.date_added}")
                print()
            
            return len(entities)
            
        except SQLAlchemyError as e:
            print(f"Error querying entities: {e}")
            return 0
    
    def verify_aliases(self):
        """
        Query the Aliases table and show alias statistics.
        
        Returns:
            Number of aliases found
        """
        try:
            print("=" * 60)
            print("ALIASES SUMMARY")
            print("=" * 60)
            
            # Query all aliases
            aliases = self.session.query(Alias).all()
            
            if not aliases:
                print("No aliases found in the database.")
                return 0
            
            print(f"Total aliases in database: {len(aliases)}")
            
            # Group aliases by entity
            entity_alias_count = {}
            for alias in aliases:
                entity_name = alias.entity.name
                if entity_name not in entity_alias_count:
                    entity_alias_count[entity_name] = []
                entity_alias_count[entity_name].append(alias.alias_name)
            
            print(f"Entities with aliases: {len(entity_alias_count)}")
            print("\nTop 10 entities by alias count:")
            
            # Sort by number of aliases and show top 10
            sorted_entities = sorted(entity_alias_count.items(), key=lambda x: len(x[1]), reverse=True)
            for i, (entity_name, aliases_list) in enumerate(sorted_entities[:10], 1):
                print(f"{i:2d}. {entity_name}: {len(aliases_list)} aliases")
                if len(aliases_list) <= 5:  # Show all aliases if 5 or fewer
                    for alias in aliases_list:
                        print(f"    - {alias}")
                else:  # Show first 3 and indicate there are more
                    for alias in aliases_list[:3]:
                        print(f"    - {alias}")
                    print(f"    ... and {len(aliases_list) - 3} more")
                print()
            
            return len(aliases)
            
        except SQLAlchemyError as e:
            print(f"Error querying aliases: {e}")
            return 0
    
    def verify_sanctions(self):
        """
        Query the Sanctions table and show sanction statistics.
        
        Returns:
            Number of sanctions found
        """
        try:
            print("=" * 60)
            print("SANCTIONS SUMMARY")
            print("=" * 60)
            
            # Query all sanctions
            sanctions = self.session.query(Sanction).all()
            
            if not sanctions:
                print("No sanctions found in the database.")
                return 0
            
            print(f"Total sanctions in database: {len(sanctions)}")
            
            # Group by sanctioning body
            sanctioning_bodies = {}
            for sanction in sanctions:
                body = sanction.sanctioning_body
                if body not in sanctioning_bodies:
                    sanctioning_bodies[body] = 0
                sanctioning_bodies[body] += 1
            
            print("\nSanctions by sanctioning body:")
            for body, count in sorted(sanctioning_bodies.items()):
                print(f"  {body}: {count} sanctions")
            
            # Group by program
            programs = {}
            for sanction in sanctions:
                program = sanction.program
                if program not in programs:
                    programs[program] = 0
                programs[program] += 1
            
            print("\nSanctions by program:")
            for program, count in sorted(programs.items()):
                print(f"  {program}: {count} sanctions")
            
            return len(sanctions)
            
        except SQLAlchemyError as e:
            print(f"Error querying sanctions: {e}")
            return 0
    
    def verify_data_integrity(self):
        """
        Verify data integrity by checking relationships.
        """
        try:
            print("=" * 60)
            print("DATA INTEGRITY CHECKS")
            print("=" * 60)
            
            # Check for entities without sanctions
            entities_without_sanctions = self.session.query(Entity).filter(
                ~Entity.sanctions.any()
            ).all()
            
            if entities_without_sanctions:
                print(f"Warning: {len(entities_without_sanctions)} entities have no sanctions:")
                for entity in entities_without_sanctions[:5]:  # Show first 5
                    print(f"  - {entity.name}")
                if len(entities_without_sanctions) > 5:
                    print(f"  ... and {len(entities_without_sanctions) - 5} more")
            else:
                print("✓ All entities have at least one sanction")
            
            # Check for aliases without entities (should not happen due to foreign keys)
            orphaned_aliases = self.session.query(Alias).filter(
                Alias.entity_id.notin_(self.session.query(Entity.id))
            ).count()
            
            if orphaned_aliases > 0:
                print(f"Warning: {orphaned_aliases} aliases have no associated entity")
            else:
                print("✓ All aliases are properly linked to entities")
            
            # Check for sanctions without entities (should not happen due to foreign keys)
            orphaned_sanctions = self.session.query(Sanction).filter(
                Sanction.entity_id.notin_(self.session.query(Entity.id))
            ).count()
            
            if orphaned_sanctions > 0:
                print(f"Warning: {orphaned_sanctions} sanctions have no associated entity")
            else:
                print("✓ All sanctions are properly linked to entities")
            
            print()
            
        except SQLAlchemyError as e:
            print(f"Error checking data integrity: {e}")
    
    def print_summary(self, entity_count, alias_count, sanction_count):
        """
        Print final summary statistics.
        
        Args:
            entity_count: Number of entities found
            alias_count: Number of aliases found
            sanction_count: Number of sanctions found
        """
        print("=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"Total entities found: {entity_count}")
        print(f"Total aliases found: {alias_count}")
        print(f"Total sanctions found: {sanction_count}")
        
        if entity_count > 0:
            print(f"Average aliases per entity: {alias_count / entity_count:.2f}")
            print(f"Average sanctions per entity: {sanction_count / entity_count:.2f}")
        
        print("=" * 60)
        print("Database verification completed successfully!")
    
    def run(self):
        """Main execution method."""
        print("Starting Database Verification")
        print("=" * 60)
        
        # Connect to database
        if not self.connect_to_database():
            print("Failed to connect to database. Exiting.")
            return False
        
        try:
            # Verify entities
            entity_count = self.verify_entities()
            
            # Verify aliases
            alias_count = self.verify_aliases()
            
            # Verify sanctions
            sanction_count = self.verify_sanctions()
            
            # Check data integrity
            self.verify_data_integrity()
            
            # Print summary
            self.print_summary(entity_count, alias_count, sanction_count)
            
            return True
            
        except Exception as e:
            print(f"Unexpected error during verification: {e}")
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
    # Check if database file exists
    db_file = "project_sentinel.db"
    if not os.path.exists(db_file):
        print(f"Error: Database file '{db_file}' not found in current directory.")
        print("Please ensure the database has been created and populated.")
        return 1
    
    # Create and run verifier
    verifier = DatabaseVerifier()
    success = verifier.run()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 