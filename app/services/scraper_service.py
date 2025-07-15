# Location: /Vibe Coding 101/app/services/scraper_service.py

#!/usr/bin/env python3
"""
MHA Banned Organizations Scraper Service (Resilient Version)

This service scrapes the MHA (Ministry of Home Affairs) banned organizations page.
It dynamically discovers all PDF links, categorizes them using keywords,
processes the data, and outputs a structured JSON file. It is designed to be
resilient to changes in link text, filenames, and the addition of new documents.
"""

import json
import logging
import os
import re
import sys
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import pdfplumber
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log', mode='w'), # Overwrite log on each run
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MHABannedOrgScraper:
    """
    A resilient scraper for MHA banned organizations data that dynamically
    discovers and categorizes PDF files.
    """
    
    def __init__(self):
        self.base_url = "https://www.mha.gov.in"
        self.banned_orgs_url = "https://www.mha.gov.in/en/divisionofmha/counter-terrorism-and-counter-radicalization-division/Banned-Organizations"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36'
        })
        
    def discover_and_categorize_pdfs(self) -> List[Dict[str, str]]:
        """
        Dynamically finds all PDF links on the page and categorizes them.
        
        Returns:
            A list of dictionaries, where each dictionary represents a found PDF
            and contains its 'url', 'text', and 'category'.
        """
        logger.info(f"Starting PDF discovery on: {self.banned_orgs_url}")
        
        try:
            response = self.session.get(self.banned_orgs_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Failed to fetch MHA page: {e}")
            return []

        found_pdfs = []
        # Find all anchor tags with an href attribute ending in '.pdf'
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.IGNORECASE))

        if not pdf_links:
            logger.error("No PDF links found on the page.")
            return []

        logger.info(f"Found {len(pdf_links)} total PDF link(s) on the page. Categorizing...")

        for link in pdf_links:
            link_text = link.get_text(strip=True)
            full_url = urljoin(self.base_url, link['href'])
            search_text = (link_text + ' ' + full_url).lower()
            
            category = 'uncategorized'
            # Categorize based on keywords
            if 'terrorist' in search_text or 'first-schedule' in search_text or 'first_schedule' in search_text or 'annexurea' in search_text:
                category = 'terrorist'
            elif 'unlawful' in search_text:
                category = 'unlawful'
            
            pdf_info = {
                'url': full_url,
                'text': link_text,
                'category': category
            }
            found_pdfs.append(pdf_info)
            logger.info(f"  - Found PDF: '{link_text}' -> Categorized as: {category}")

        return found_pdfs

    def download_pdf(self, url: str, category: str) -> Optional[str]:
        """Downloads a PDF and returns the local file path."""
        try:
            logger.info(f"Downloading {category} PDF from: {url}")
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
            
            filename = f"{category}_{os.path.basename(urlparse(url).path)}"
            filepath = os.path.join('/tmp', filename) # Save to a temporary directory

            with open(filepath, 'wb') as f:
                f.write(response.content)
            logger.info(f"Successfully downloaded to: {filepath}")
            return filepath
            
        except requests.RequestException as e:
            logger.error(f"Error downloading PDF {url}: {e}")
            return None

    def parse_name_and_aliases(self, raw_name_string: str) -> (str, List[str]):
        """
        Cleans a raw string, extracts the primary name, and derives a rich set of aliases
        including from slashes, parentheses, acronyms, and spelling variations.
        """
        if not isinstance(raw_name_string, str):
            return "", []

        # 1. Initial Cleaning
        clean_str = re.sub(r'\s+', ' ', raw_name_string).strip()
        
        # 2. Extract Primary Name (text before the first slash or parenthesis)
        primary_name_match = re.match(r'^(.*?)(?:\s*\(|\s*\/|$)', clean_str)
        primary_name = primary_name_match.group(1).strip() if primary_name_match else clean_str
        
        # 3. Extract Aliases from Slashes and Parentheses
        aliases = set()
        # Add all parts separated by slashes
        for part in clean_str.split('/'):
            # Remove any nested parentheses for the alias list
            alias = re.sub(r'\(.*?\)', '', part).strip()
            if len(alias) > 2:
                aliases.add(alias)
        
        # Add all parts found inside parentheses
        paren_matches = re.findall(r'\((.*?)\)', clean_str)
        for match in paren_matches:
            # Can have multiple aliases inside, separated by comma or semicolon
            for part in re.split(r'[,;]', match):
                if len(part.strip()) > 2:
                    aliases.add(part.strip())

        # 4. Generate Acronym for the primary name
        words = re.findall(r'\b[A-Za-z]+\b', primary_name)
        stop_words = {'of', 'the', 'and', 'ul', 'e', 'in'}
        acronym = "".join([word[0] for word in words if word.lower() not in stop_words]).upper()
        if len(acronym) >= 2:
            aliases.add(acronym)

        # 5. Generate Spelling Variations (e.g., Al-Qaida vs Al-Qaeda)
        spelling_variations = set()
        for alias in aliases.copy(): # Iterate over a copy as we modify the set
            if 'qaida' in alias.lower():
                spelling_variations.add(re.sub(r'qaida', 'qaeda', alias, flags=re.IGNORECASE))
            if 'qaeda' in alias.lower():
                spelling_variations.add(re.sub(r'qaeda', 'qaida', alias, flags=re.IGNORECASE))
        aliases.update(spelling_variations)

        # 6. Final Cleanup
        # Remove the primary name itself from the alias list
        aliases.discard(primary_name)
        # Remove any aliases that are substrings of the primary name
        aliases = {alias for alias in aliases if alias.lower() not in primary_name.lower()}
        
        return primary_name, sorted(list(aliases))


    def extract_data_from_pdf(self, pdf_path: str, category: str) -> List[Dict]:
        """Extracts organization data from a single PDF file."""
        organizations = []
        logger.info(f"Extracting data from {pdf_path}")
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    tables = page.extract_tables()
                    if not tables:
                        logger.warning(f"No tables found on page {page_num} of {pdf_path}. Skipping.")
                        continue

                    for table in tables:
                        # Skip header rows
                        for row in table[1:]:
                            if not row or not any(cell for cell in row if cell):
                                continue
                            # The name is usually in the second column (index 1)
                            raw_name = row[1]
                            if raw_name and len(raw_name.strip()) > 3:
                                primary_name, aliases = self.parse_name_and_aliases(raw_name)
                                if primary_name:
                                    organizations.append({
                                        'name': primary_name,
                                        'aliases': aliases,
                                        'category': category,
                                        'source': 'MHA India'
                                    })
        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_path}: {e}", exc_info=True)
        
        logger.info(f"Extracted {len(organizations)} organizations from {pdf_path}")
        return organizations

    def deduplicate_and_save(self, organizations: List[Dict]):
        """Deduplicates a list of organizations and saves to JSON."""
        if not organizations:
            logger.warning("No organizations were extracted. Nothing to save.")
            return

        unique_orgs = {org['name'].lower(): org for org in organizations}
        deduplicated_list = list(unique_orgs.values())
        
        logger.info(f"Deduplicated {len(organizations)} -> {len(deduplicated_list)} organizations.")
        
        output_filename = 'mha_banned_list.json'
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(deduplicated_list, f, ensure_ascii=False, indent=2)
            logger.info(f"Successfully saved {len(deduplicated_list)} organizations to {output_filename}")
        except IOError as e:
            logger.error(f"Failed to save JSON file: {e}")

    def run(self):
        """Main execution method to run the full scraping pipeline."""
        logger.info("="*50)
        logger.info("Starting MHA Banned Organizations Scraper (Resilient Mode)")
        logger.info("="*50)
        
        # 1. Discover and categorize all PDFs on the page
        discovered_pdfs = self.discover_and_categorize_pdfs()
        if not discovered_pdfs:
            logger.error("Scraper run failed: No PDFs were discovered.")
            return

        all_organizations = []
        temp_files_to_clean = []

        # 2. Process each categorized PDF
        for pdf_info in discovered_pdfs:
            if pdf_info['category'] == 'uncategorized':
                logger.critical(f"CRITICAL: Found new, uncategorized PDF '{pdf_info['text']}' at {pdf_info['url']}. Manual review required. Skipping file.")
                continue

            # Download the PDF
            local_pdf_path = self.download_pdf(pdf_info['url'], pdf_info['category'])
            if not local_pdf_path:
                continue
            
            temp_files_to_clean.append(local_pdf_path)
            
            # Extract data from the downloaded PDF
            orgs = self.extract_data_from_pdf(local_pdf_path, pdf_info['category'])
            all_organizations.extend(orgs)

        # 3. Deduplicate and save the final combined list
        self.deduplicate_and_save(all_organizations)

        # 4. Clean up temporary files
        logger.info("Cleaning up temporary PDF files...")
        for f in temp_files_to_clean:
            try:
                os.remove(f)
                logger.info(f"  - Removed {f}")
            except OSError as e:
                logger.warning(f"Could not remove temp file {f}: {e}")
        
        logger.info("="*50)
        logger.info("Scraping pipeline finished.")
        logger.info("="*50)

def main():
    """Main entry point."""
    scraper = MHABannedOrgScraper()
    scraper.run()

if __name__ == "__main__":
    main()
