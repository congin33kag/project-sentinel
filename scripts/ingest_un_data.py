#!/usr/bin/env python3
import logging
import requests
import xml.etree.ElementTree as ET
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

XML_URL = 'https://scsanctions.un.org/resources/xml/en/consolidated.xml'
OUTPUT_JSON = 'un_consolidated_list.json'

def main():
    logging.info('Downloading UN Consolidated Sanctions List XML...')
    response = requests.get(XML_URL)
    response.raise_for_status()
    xml_content = response.content
    
    logging.info('Parsing XML...')
    root = ET.fromstring(xml_content)
    
    records = []
    individual_count = 0
    entity_count = 0
    
    # Process INDIVIDUALS
    for individual in root.findall('.//INDIVIDUAL'):
        first_name = individual.find('FIRST_NAME').text if individual.find('FIRST_NAME') is not None else ''
        second_name = individual.find('SECOND_NAME').text if individual.find('SECOND_NAME') is not None else ''
        third_name = individual.find('THIRD_NAME').text if individual.find('THIRD_NAME') is not None else ''
        fourth_name = individual.find('FOURTH_NAME').text if individual.find('FOURTH_NAME') is not None else ''
        primary_name = ' '.join([name for name in [first_name, second_name, third_name, fourth_name] if name]).strip()
        
        aliases = []
        for alias in individual.findall('INDIVIDUAL_ALIAS'):
            alias_name = alias.find('ALIAS_NAME').text if alias.find('ALIAS_NAME') is not None else ''
            if alias_name:
                aliases.append(alias_name)
        orig_script = individual.find('NAME_ORIGINAL_SCRIPT').text if individual.find('NAME_ORIGINAL_SCRIPT') is not None else ''
        if orig_script and orig_script not in aliases:
            aliases.append(orig_script)
        
        if primary_name:
            records.append({
                'primary_name': primary_name,
                'aliases': aliases,
                'category': 'individual',
                'source': 'UNSC'
            })
            individual_count += 1
    
    # Process ENTITIES
    for entity in root.findall('.//ENTITY'):
        primary_name = entity.find('FIRST_NAME').text if entity.find('FIRST_NAME') is not None else ''
        
        aliases = []
        for alias in entity.findall('ENTITY_ALIAS'):
            alias_name = alias.find('ALIAS_NAME').text if alias.find('ALIAS_NAME') is not None else ''
            if alias_name:
                aliases.append(alias_name)
        orig_script = entity.find('NAME_ORIGINAL_SCRIPT').text if entity.find('NAME_ORIGINAL_SCRIPT') is not None else ''
        if orig_script and orig_script not in aliases:
            aliases.append(orig_script)
        
        if primary_name:
            records.append({
                'primary_name': primary_name,
                'aliases': aliases,
                'category': 'entity',
                'source': 'UNSC'
            })
            entity_count += 1
    
    logging.info(f'Processed {individual_count} individuals and {entity_count} entities')
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    
    logging.info(f'Data saved to {OUTPUT_JSON}')

if __name__ == '__main__':
    main() 