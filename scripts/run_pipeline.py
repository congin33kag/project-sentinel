#!/usr/bin/env python3
import sys
import logging
from app.services.scraper_service import MHABannedOrgScraper
from scripts.ingest_un_data import main as un_main
from scripts.ingest_ofac_data import main as ofac_main
from scripts.ingest_data import main as ingest_main

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_pipeline():
    logging.info('Starting pipeline...')
    
    logging.info('Running MHA scraper...')
    mha_scraper = MHABannedOrgScraper()
    mha_success = mha_scraper.scrape_and_save()
    if not mha_success:
        logging.error('MHA scraper failed')
        sys.exit(1)
    logging.info('MHA scraper completed')
    
    logging.info('Running UN data ingest...')
    un_main()
    logging.info('UN data ingest completed')
    
    logging.info('Running OFAC data ingest...')
    ofac_main()
    logging.info('OFAC data ingest completed')
    
    logging.info('Running main data ingestion...')
    ingest_main()
    logging.info('Main data ingestion completed')
    
    logging.info('Pipeline completed successfully')

if __name__ == '__main__':
    run_pipeline() 