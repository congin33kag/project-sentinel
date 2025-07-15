#!/usr/bin/env python3
"""
OFAC SDN List Scraper Service

This service downloads and parses the U.S. Treasury's Specially Designated Nationals (SDN) list
from the official CSV source. It extracts entity information including names, aliases, and 
categories, then saves the data to a JSON file compatible with the existing data structure.
"""

import csv
import json
import logging
import os
import re
import sys
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ofac_scraper.log', mode='w'),  # Overwrite log on each run
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class OFACSDNScraper:
    """
    A scraper for OFAC SDN (Specially Designated Nationals) list that downloads
    the official CSV file and extracts entity information.
    """
    
    def __init__(self):
        self.sdn_url = "https://www.treasury.gov/ofac/downloads/sdn.csv"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36'
        })
        
    def download_sdn_csv(self) -> Optional[str]:
        """
        Download the SDN CSV file from OFAC website.
        
        Returns:
            Optional[str]: Path to the downloaded CSV file, or None if download failed
        """
        try:
            logger.info(f"Downloading SDN CSV from: {self.sdn_url}")
            response = self.session.get(self.sdn_url, timeout=30)
            response.raise_for_status()
            
            # Save to temporary file
            csv_path = "sdn_temp.csv"
            with open(csv_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            logger.info(f"Successfully downloaded SDN CSV to: {csv_path}")
            return csv_path
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download SDN CSV: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading SDN CSV: {e}")
            return None
    
    def parse_name_and_aliases(self, alias_field: str) -> Tuple[str, List[str]]:
        """
        Parse aliases from the alias field (column 11).
        
        The alias field contains formats like:
        - "a.k.a. 'ALIAS1'; a.k.a. 'ALIAS2'"
        - "f.k.a. 'FORMER NAME'"
        - "n.k.a. 'NEW NAME'"
        
        Args:
            alias_field (str): The raw alias field from the CSV
            
        Returns:
            Tuple[str, List[str]]: (empty_string, list_of_aliases)
        """
        if not alias_field or alias_field == "-0-":
            return "", []
        
        # Clean up the alias field
        alias_field = alias_field.strip()
        
        aliases = []
        
        # Pattern to match aliases: a.k.a. 'ALIAS', f.k.a. 'ALIAS', n.k.a. 'ALIAS'
        # Also handle cases without quotes
        alias_pattern = r'(?:a\.k\.a\.|f\.k\.a\.|n\.k\.a\.)\s*[\'"]?([^\'";,]+)[\'"]?'
        matches = re.findall(alias_pattern, alias_field, re.IGNORECASE)
        
        for match in matches:
            alias = match.strip()
            if alias and alias not in aliases:
                # Remove any trailing punctuation
                alias = re.sub(r'[\.;,]+$', '', alias).strip()
                if alias:
                    aliases.append(self.clean_name(alias))
        
        # Also try a simpler pattern for cases like "a.k.a. BNC" without quotes
        simple_pattern = r'(?:a\.k\.a\.|f\.k\.a\.|n\.k\.a\.)\s+([^;,\.]+)'
        simple_matches = re.findall(simple_pattern, alias_field, re.IGNORECASE)
        
        for match in simple_matches:
            alias = match.strip()
            if alias and alias not in aliases:
                # Remove any trailing punctuation
                alias = re.sub(r'[\.;,]+$', '', alias).strip()
                if alias:
                    cleaned_alias = self.clean_name(alias)
                    if cleaned_alias and cleaned_alias not in aliases:
                        aliases.append(cleaned_alias)
        
        # Remove duplicates and empty strings
        aliases = [alias for alias in aliases if alias]
        aliases = list(dict.fromkeys(aliases))  # Remove duplicates while preserving order
        
        return "", aliases
    
    def clean_name(self, name: str) -> str:
        """
        Clean and normalize a name string.
        
        Args:
            name (str): Raw name string
            
        Returns:
            str: Cleaned name string
        """
        if not name:
            return ""
        
        # Remove surrounding quotes
        name = name.strip('\'"')
        
        # Remove extra whitespace and normalize
        name = re.sub(r'\s+', ' ', name.strip())
        
        # Remove common prefixes/suffixes that might be inconsistent
        name = re.sub(r'^(Mr\.?|Mrs\.?|Ms\.?|Dr\.?)\s+', '', name, flags=re.IGNORECASE)
        
        return name
    
    def parse_csv_data(self, csv_path: str) -> List[Dict[str, any]]:
        """
        Parse the SDN CSV file and extract entity information.
        
        Args:
            csv_path (str): Path to the CSV file
            
        Returns:
            List[Dict[str, any]]: List of extracted entities
        """
        entities = []
        processed_count = 0
        skipped_count = 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                # Read CSV with proper handling
                reader = csv.reader(csvfile)
                
                logger.info("Starting to parse CSV data...")
                
                for row_num, row in enumerate(reader, 1):
                    if len(row) < 12:  # Need at least 12 columns for alias info
                        continue
                    
                    # Extract data from columns
                    # Column 0: ent_num (entity number)
                    # Column 1: SDN_Name (primary name)
                    # Column 2: SDN_Type (entity type - individual, vessel, or empty for entities)
                    # Column 11: Aliases (a.k.a. information)
                    entity_type = row[2].strip().lower() if len(row) > 2 else ""
                    
                    # Map entity types - if column 2 is empty, it's usually an entity
                    if entity_type == "individual":
                        category = "individual"
                    elif entity_type == "vessel":
                        category = "vessel"  # Keep vessels separate
                    elif entity_type == "" or entity_type == "-0-":
                        category = "entity"  # Empty usually means entity
                    else:
                        # Skip unknown types
                        skipped_count += 1
                        continue
                    
                    # Only process individuals and entities (skip vessels for now)
                    if category not in ['individual', 'entity']:
                        skipped_count += 1
                        continue
                    
                    name_field = row[1].strip() if len(row) > 1 else ""
                    if not name_field:
                        skipped_count += 1
                        continue
                    
                    # Clean the primary name
                    primary_name = self.clean_name(name_field)
                    
                    if not primary_name:
                        skipped_count += 1
                        continue
                    
                    # Extract aliases from column 11
                    aliases = []
                    alias_field = row[11].strip() if len(row) > 11 else ""
                    if alias_field and alias_field != "-0-":
                        # Parse aliases from the alias field
                        _, parsed_aliases = self.parse_name_and_aliases(alias_field)
                        aliases = parsed_aliases
                    
                    # Create entity record
                    entity = {
                        "name": primary_name,
                        "aliases": aliases,
                        "category": category,
                        "source": "US OFAC"
                    }
                    
                    entities.append(entity)
                    processed_count += 1
                    
                    # Log progress every 1000 records
                    if processed_count % 1000 == 0:
                        logger.info(f"Processed {processed_count} records...")
                
                logger.info(f"Parsing complete. Processed: {processed_count}, Skipped: {skipped_count}")
                
        except Exception as e:
            logger.error(f"Error parsing CSV data: {e}")
            return []
        
        return entities
    
    def save_to_json(self, entities: List[Dict[str, any]], output_path: str = "ofac_sdn_list.json") -> bool:
        """
        Save the extracted entities to a JSON file.
        
        Args:
            entities (List[Dict[str, any]]): List of entities to save
            output_path (str): Path to save the JSON file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(entities, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully saved {len(entities)} entities to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving JSON file: {e}")
            return False
    
    def cleanup_temp_files(self):
        """Clean up temporary files created during processing."""
        temp_files = ["sdn_temp.csv"]
        
        for file_path in temp_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up temporary file: {file_path}")
                except Exception as e:
                    logger.warning(f"Could not remove temporary file {file_path}: {e}")
    
    def scrape_and_save(self, output_path: str = "ofac_sdn_list.json") -> bool:
        """
        Main method to scrape OFAC SDN data and save to JSON.
        
        Args:
            output_path (str): Path to save the JSON file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Starting OFAC SDN scraping process...")
            
            # Download CSV file
            csv_path = self.download_sdn_csv()
            if not csv_path:
                logger.error("Failed to download SDN CSV file")
                return False
            
            # Parse CSV data
            entities = self.parse_csv_data(csv_path)
            if not entities:
                logger.error("No entities extracted from CSV")
                return False
            
            # Save to JSON
            success = self.save_to_json(entities, output_path)
            
            # Cleanup temporary files
            self.cleanup_temp_files()
            
            if success:
                logger.info(f"OFAC SDN scraping completed successfully. Total entities: {len(entities)}")
                return True
            else:
                logger.error("Failed to save entities to JSON")
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error during scraping: {e}")
            self.cleanup_temp_files()
            return False


def main():
    """Main function to run the OFAC SDN scraper."""
    scraper = OFACSDNScraper()
    success = scraper.scrape_and_save()
    
    if success:
        logger.info("OFAC SDN scraping completed successfully!")
        sys.exit(0)
    else:
        logger.error("OFAC SDN scraping failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 