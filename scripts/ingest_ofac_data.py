#!/usr/bin/env python3
import logging
import pandas as pd
import re
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CSV_URL = 'https://www.treasury.gov/ofac/downloads/sdn.csv'
OUTPUT_JSON = 'ofac_sdn_list.json'

def parse_aliases(remarks):
    if pd.isna(remarks):
        return []
    aliases = re.findall(r'\baka (.+?)\b', remarks, re.IGNORECASE)
    return [alias.strip() for alias in aliases if alias.strip()]

def main():
    logging.info('Downloading OFAC SDN List CSV...')
    df = pd.read_csv(CSV_URL, header=None)
    # Columns based on OFAC format: 0: ent_num, 1: sdn_name, 2: sdn_type, etc.
    df.columns = ['ent_num', 'sdn_name', 'sdn_type', 'program', 'title', 'call_sign', 'vsl_type', 'tonnage', 'grt', 'vsl_flag', 'vsl_owner', 'remarks']
    
    records = []
    total_records = len(df)
    
    for index, row in df.iterrows():
        primary_name = row['sdn_name']
        category = row['sdn_type'].lower() if pd.notna(row['sdn_type']) else 'unknown'
        aliases = parse_aliases(row['remarks'])
        
        if primary_name:
            records.append({
                'primary_name': primary_name,
                'aliases': aliases,
                'category': category,
                'source': 'US OFAC'
            })
        
        if (index + 1) % 1000 == 0:
            logging.info(f'Processed {index + 1}/{total_records} records')
    
    logging.info(f'Processed {total_records} total records')
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    
    logging.info(f'Data saved to {OUTPUT_JSON}')

if __name__ == '__main__':
    main() 