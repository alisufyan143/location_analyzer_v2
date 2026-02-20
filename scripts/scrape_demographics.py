
import sys
import pandas as pd
from pathlib import Path
import time

# Add src to path
sys.path.append(str(Path.cwd() / "src"))

from location_analyzer.scrapers.streetcheck import DemographicsScraper
from location_analyzer.logging_config import get_logger

logger = get_logger(__name__)

INPUT_FILE = Path(r"data/processed/v2_enriched_sales.csv")
OUTPUT_FILE = Path(r"data/processed/v2_enriched_sales.csv") # Overwrite or new file? Overwrite to fill gaps.

def scrape_missing_demographics():
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found.")
        return

    print("--- Starting Demographics Scraping ---")
    df = pd.read_csv(INPUT_FILE)
    
    # 1. Identify rows needing scraping
    # We need scraping if:
    # a) we have a postcode (or outercode)
    # b) demographic fields are missing (e.g. 'population' is NaN)
    
    # Ensure outercode exists
    if 'outercode' not in df.columns:
        df['outercode'] = None
        
    def get_outercode(row):
        if pd.notna(row['outercode']):
            return row['outercode']
        if pd.notna(row['postcode']):
            return row['postcode'].split()[0].strip()
        return None

    df['outercode'] = df.apply(get_outercode, axis=1)
    
    # Valid targets: Has outercode, missing population
    mask_target = df['outercode'].notna() & df['population'].isna()
    target_outercodes = df.loc[mask_target, 'outercode'].unique()
    
    print(f"Found {len(target_outercodes)} unique outercodes to scrape.")
    print(f"Examples: {target_outercodes[:5]}")
    
    if len(target_outercodes) == 0:
        print("No missing demographics found.")
        return

    # 2. Scrape
    scraper = DemographicsScraper()
    results = {}
    
    # Access the mapping from the imported module
    from location_analyzer.scrapers.streetcheck import OUTERCODE_TO_TOWN

    for i, outercode in enumerate(target_outercodes):
        print(f"[{i+1}/{len(target_outercodes)}] Scraping {outercode}...")
        
        # Heuristic: If outercode is NOT in our mapping, it's likely outside London/Home Counties
        # PostcodeArea needs exact town name. If we don't know it, it defaults to London -> 404/Bad Data.
        # So for unknown codes, try StreetCheck first/only.
        
        # Check mapping
        is_known = outercode in OUTERCODE_TO_TOWN
        if not is_known:
            # Check prefix match as scraper does
            import re
            match = re.match(r"([A-Z]+\d+)", outercode)
            if match and match.group(1) in OUTERCODE_TO_TOWN:
                is_known = True

        data = None
        try:
            if is_known:
                # Use standard scraper flow (try PostcodeArea first)
                data = scraper.scrape(outercode)
            else:
                # Unknown town -> Prioritize StreetCheck
                # We can call internal method or just rely on fallback?
                # Relying on fallback is risky if PostcodeArea returns garbage for "London" query.
                # Let's try StreetCheck URL construction directly.
                print(f"  -> Unknown town for {outercode}, trying StreetCheck directly...")
                url_sc = f"{scraper.STREETCHECK_BASE_URL}/{outercode}"
                soup = scraper._fetch_with_playwright(url_sc, outercode)
                data = scraper._parse_streetcheck(soup, outercode)
                
            if data:
                results[outercode] = data
            else:
                results[outercode] = None
                
        except Exception as e:
            print(f"Failed to scrape {outercode}: {e}")
            results[outercode] = None
        
        # Be nice to the server
        time.sleep(2)
            
    # 3. Update DataFrame
    print("Updating dataset...")
    
    # Columns map from scraper output to DataFrame columns
    # Scraper keys: population, households, avg_household_income, unemployment_rate, working, unemployed, ab, c1_c2, de, white, non_white
    # DF columns: population, households, avg_household_income, unemployment_rate, working, unemployed, ab, c1/c2, de, white, non-white
    
    col_map = {
        "c1_c2": "c1/c2",
        "non_white": "non-white"
    }
    
    updated_count = 0
    
    for idx, row in df[mask_target].iterrows():
        oc = row['outercode']
        if oc in results and results[oc]:
            data = results[oc]
            
            # Update fields
            for key, val in data.items():
                df_col = col_map.get(key, key)
                if df_col not in df.columns:
                    df[df_col] = None
                
                # Update if missing or overwrite?
                # Target mask was "missing population", so generally safe to overwrite
                df.at[idx, df_col] = val
                
            updated_count += 1
            
    print(f"Updated {updated_count} rows with scraped data.")
    
    # Save
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    scrape_missing_demographics()
