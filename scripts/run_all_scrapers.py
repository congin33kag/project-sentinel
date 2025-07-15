#!/usr/bin/env python3
"""
Run All Scrapers

This script serves as a single entry point to run all data scrapers sequentially:
1. MHA Banned Organizations Scraper
2. OFAC SDN List Scraper

It provides status updates for each scraper.
"""

import sys

from app.services.scraper_service import MHABannedOrgScraper
from app.services.ofac_scraper_service import OFACSDNScraper

def main():
    """Main function to run all scrapers sequentially."""
    
    print("--- Starting MHA Scraper ---")
    mha_scraper = MHABannedOrgScraper()
    mha_success = mha_scraper.scrape_and_save()
    if mha_success:
        print("--- MHA Scraper Finished Successfully ---")
    else:
        print("--- MHA Scraper Failed ---")
    
    print("--- Starting OFAC Scraper ---")
    ofac_scraper = OFACSDNScraper()
    ofac_success = ofac_scraper.scrape_and_save()
    if ofac_success:
        print("--- OFAC Scraper Finished Successfully ---")
    else:
        print("--- OFAC Scraper Failed ---")
    
    if mha_success and ofac_success:
        print("All scrapers completed successfully!")
        sys.exit(0)
    else:
        print("One or more scrapers failed.")
        sys.exit(1)

if __name__ == "__main__":
    main() 