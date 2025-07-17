import os
import sys
import json
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to the path to allow imports from 'app'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the database models
from app.models.entity import Base, Entity, Alias, Sanction

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Main Ingestion Logic ---
def main():
    """
    Main function to clear and populate the database using high-performance
    batch processing with robust data validation.
    """
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./project_sentinel.db")
    
    logging.info(f"--- Data Ingestion Started ---")
    logging.info(f"Attempting to connect to database: {DATABASE_URL}")

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        logging.info("Clearing existing data from database...")
        session.query(Sanction).delete()
        session.query(Alias).delete()
        session.query(Entity).delete()
        session.commit()
        logging.info("Database tables cleared successfully.")

        logging.info("Processing data files and preparing batch...")
        
        files_to_process = {
            'mha_banned_list.json': 'MHA India',
            'ofac_sdn_list.json': 'US OFAC',
            'un_consolidated_list.json': 'UNSC'
        }
        
        all_objects_to_add = []
        items_processed = 0
        items_skipped = 0

        for filename, source_body in files_to_process.items():
            if not os.path.exists(filename):
                logging.warning(f"Data file not found: {filename}. Skipping.")
                continue

            logging.info(f"Loading data from {filename}...")
            with open(filename, 'r') as f:
                data = json.load(f)
            
            for item in data:
                items_processed += 1
                
                raw_name = item.get('primary_name') or item.get('name')
                
                # --- THE FIX IS HERE ---
                # 1. Ensure the raw_name is not None.
                # 2. Convert it to a string to handle potential numbers (floats).
                # 3. Then, safely strip whitespace.
                if raw_name is not None:
                    primary_name = str(raw_name).strip()
                else:
                    primary_name = None

                if primary_name:
                    new_entity = Entity(
                        name=primary_name,
                        type=item.get('list_type') or item.get('category', 'organization'),
                        source=source_body
                    )
                    
                    if item.get('aliases'):
                        for alias_name in item['aliases']:
                            if isinstance(alias_name, str):
                                new_alias = Alias(alias_name=alias_name, entity=new_entity)
                                all_objects_to_add.append(new_alias)
                            else:
                                logging.warning(f"Skipping non-string alias for entity {primary_name}: {alias_name}")

                    all_objects_to_add.append(new_entity)
                else:
                    items_skipped += 1
                    logging.warning(f"Skipping record due to missing primary name. Record: {item}")

        logging.info(f"Total items processed: {items_processed}. Items skipped: {items_skipped}.")
        logging.info(f"Batch prepared with {len(all_objects_to_add)} total objects.")

        logging.info("Committing batch to the database. This may take a moment...")
        session.add_all(all_objects_to_add)
        session.commit()
        
        logging.info(f"--- Successfully finished populating the database ---")

    except Exception as e:
        logging.error(f"An error occurred during ingestion: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    main()
