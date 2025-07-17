#!/usr/bin/env python3
import logging
import os
import sys
import pandas as pd
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.models.entity import Base, Entity, Relationship

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main(csv_file='company_master_data.csv'):
    database_url = os.getenv('DATABASE_URL', 'sqlite:///./project_sentinel.db')
    logging.info(f'Connecting to database: {database_url}')
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    
    logging.info(f'Reading CSV file: {csv_file}')
    df = pd.read_csv(csv_file)
    
    with Session() as session:
        for index, row in df.iterrows():
            company_name = row.get('COMPANY_NAME')  # Assume column name
            if not company_name:
                logging.warning(f'Skipping row {index}: No company name')
                continue
            
            # Check if company exists
            company = session.query(Entity).filter(func.lower(Entity.name) == company_name.lower(), Entity.type == 'organization').first()
            if not company:
                company = Entity(name=company_name, type='organization', source='MCA India')
                session.add(company)
                session.flush()
            
            # Assume directors are in a column 'DIRECTORS' comma-separated
            directors_str = row.get('DIRECTORS', '')
            director_names = [name.strip() for name in directors_str.split(',') if name.strip()]
            
            for dir_name in director_names:
                director = session.query(Entity).filter(func.lower(Entity.name) == dir_name.lower(), Entity.type == 'person').first()
                if not director:
                    director = Entity(name=dir_name, type='person', source='MCA India')
                    session.add(director)
                    session.flush()
                
                # Create relationship if not exists
                rel = session.query(Relationship).filter(
                    Relationship.from_entity_id == director.id,
                    Relationship.to_entity_id == company.id,
                    Relationship.relation_type == 'Director Of'
                ).first()
                if not rel:
                    rel = Relationship(from_entity_id=director.id, to_entity_id=company.id, relation_type='Director Of')
                    session.add(rel)
            
            session.commit()
            if (index + 1) % 100 == 0:
                logging.info(f'Processed {index + 1} rows')
    
    logging.info('Ingestion completed')

if __name__ == '__main__':
    main() 