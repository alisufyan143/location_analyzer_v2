
import pandas as pd
from pathlib import Path

INGESTED_PATH = Path(r"data/raw/v2_ingested_sales.csv")
MASTER_PATH = Path(r"data/raw/v1_2025_06/sales_data.xlsx")
OUTPUT_PATH = Path(r"data/processed/v2_enriched_sales.csv")

# Manual mapping for disparate branch names (v2 -> v1)
BRANCH_MAPPING = {
    "Grillo Piri Piri": "piri piri grillo",
    "Galos Hamilton": "galos peri peri hamilton",
    "Galos Kilmarnock": "galos peri peri kilmarnock",
    # JojoPeri, The Grill -> Not found
}

# Manual postcode overrides for branches missing in Master
POSTCODE_OVERRIDES = {
    "Galos Hamilton": "KA21 5DT",   # 43 Hamilton St, Saltcoats
    "Galos Kilmarnock": "KA1 1PG",  # 104-106 King St, Kilmarnock
    "JojoPeri": "TW9 2ND",
    "The Grill Peri Peri": "CB1 2AS",
}

def enrich_data():
    if not INGESTED_PATH.exists():
        print(f"Error: {INGESTED_PATH} not found.")
        return

    print("--- Starting Enrichment ---")
    
    # 1. Load Data
    df_new = pd.read_csv(INGESTED_PATH)
    print(f"Loaded {len(df_new)} rows from {INGESTED_PATH}")
    
    # 2. Load Master Lookup
    # We need: Branch Name -> Postcode, Demographics...
    # Master usually has multiple rows per branch (daily sales).
    # We just need ONE row per branch to get the static info.
    print(f"Loading Master Dataset from {MASTER_PATH}...")
    df_master = pd.read_excel(MASTER_PATH)
    
    # Dedup Master to get unique Branch -> Details
    # Columns to keep for enrichment
    keep_cols = [
        'Branch Name', 'postcode', 'outercode', 'shopname', 
        'population', 'households', 'avg_household_income', 
        'unemployment_rate', 'working', 'unemployed', 
        'ab', 'c1/c2', 'de', 'white', 'non-white',
        'Distance_to_Nearest_Station', 'Nearby_Station_Count',
        'Nearest_Station_Type', 'Transport_Accessibility_Score'
    ]
    # Ensure columns exist
    keep_cols = [c for c in keep_cols if c in df_master.columns]
    
    # Create Lookup DataFrame
    # Drop duplicates by Branch Name to get a unique key
    df_lookup = df_master[keep_cols].drop_duplicates(subset=['Branch Name'])
    # Convert Branch Name to lower for matching? No, manual mapping handles it.
    
    # 3. Apply Mapping to v2 Data
    # Create a temporary 'Join_Key' column
    df_new['Join_Key'] = df_new['Brand Name'].astype(str) # Default to Brand Name (e.g. Grillo Piri Piri)
    # Check if we should use Branch Name?
    # In v2, for Grillo/Galos, Branch Name is "Main". Brand Name is "Grillo Piri Piri".
    # For Rios/Maemes, Branch Name is "Ilford". Brand Name is "Rios".
    # So:
    # If Brand is in Mapping Keys -> Use Mapping[Brand] as Join Key
    # Else -> Use Branch Name + Brand Name?
    # Actually, master has 'Branch Name'.
    
    # Strategy:
    # a) If we ALREADY have a postcode (Maemes/Rios), strict keep.
    # b) If postcode is MISSING, try to join.
    
    rows_before = len(df_new)
    
    # Helper to find join key
    def get_join_key(row):
        # 1. Check if specific Brand Name is in our mapping
        brand = str(row['Brand Name']).strip()
        if brand in BRANCH_MAPPING:
            return BRANCH_MAPPING[brand]
        
        # 2. Check Branch Name (for Maemes/Rios if we wanted to enrich existing, but we have PC)
        # We only care about MISSING pc rows for now.
        return None

    df_new['Master_Branch_Match'] = df_new.apply(get_join_key, axis=1)
    
    # 4. Merge
    # We only want to fill missing columns.
    # But for simplicity, let's join on 'Master_Branch_Match' -> 'Branch Name' (Master)
    # And fillna.
    
    # Separate DF into "Has Postcode" and "Needs Enrichment"
    # Actually, even if it has postcode, we might want demographics from Master?
    # Yes! Maemes/Rios *might* be in Master (e.g. Rios Ilford).
    # If they are in Master, we want their demographics.
    # If not, we keep their postcode and scrape later.
    
    # Better Join Strategy:
    # Try to match v2 'Branch Name' (or Brand) to v1 'Branch Name'.
    
    # Let's standardize keys
    df_lookup['Join_Branch'] = df_lookup['Branch Name'].str.lower().str.strip()
    
    # Add Join_Branch to df_new
    # For Grillo/Galos: Use Mapped Value
    # For Rios/Maemes: Use "Brand + Branch"? 
    #   v2: Brand="Rios", Branch="Ilford".
    #   v1: Branch="rios piri piri ilford".
    #   We need to construct "rios piri piri ilford" from "Rios" + "Ilford".
    
    def construct_join_key(row):
        brand = str(row['Brand Name']).strip()
        branch = str(row['Branch Name']).strip()
        
        # Explicit Map First
        if brand in BRANCH_MAPPING:
            return BRANCH_MAPPING[brand].lower()
        
        # Construct for Rios/Maemes
        # Try: "brand branch"
        # e.g. "Rios Ilford" -> "rios piri piri ilford" (fuzzy?)
        # Master entries are consistently "rios piri piri [location]" or "maeme's [location]" or "maemes [location]"?
        # We need a fuzzy matcher or smart construction.
        
        # Simple construction:
        candidate = f"{brand} {branch}".lower()
        # Clean specific constructs
        candidate = candidate.replace("rios", "rios piri piri").replace("maemes", "maeme's")
        # This is risky.
        
        return candidate

    # For now, let's ONLY target the ONES WITH MISSING POSTCODES (Grillo, Galos).
    # Because Rios/Maemes have postcodes, we can use StreetCheck later if Master match fails.
    
    mask_missing = df_new['postcode'].isna()
    print(f"Rows with missing postcode: {mask_missing.sum()}")
    
    # Update Join Key for missing only
    df_new.loc[mask_missing, 'Join_Branch'] = df_new.loc[mask_missing].apply(
        lambda r: BRANCH_MAPPING.get(r['Brand Name'], None), axis=1
    )
    
    # Merge
    # We assume lookup has unique 'Branch Name'.
    # Join on 'Join_Branch' (v2) == 'Branch Name' (v1, normalized?)
    # df_lookup index on 'Join_Branch'?
    
    # Create dictionary from lookup for speed/simplicity
    lookup_dict = df_lookup.set_index('Join_Branch').to_dict('index')
    
    enriched_count = 0
    
    for idx, row in df_new[mask_missing].iterrows():
        # 1. Check Overrides first
        brand_key = row['Brand Name']
        if brand_key in POSTCODE_OVERRIDES:
            df_new.at[idx, 'postcode'] = POSTCODE_OVERRIDES[brand_key]
            # No demographics yet, but at least we have PC for scraping
            enriched_count += 1
            continue

        # 2. Check Master Lookup
        key = row['Join_Branch']
        if key and isinstance(key, str):
            key_lower = key.lower()
            if key_lower in lookup_dict:
                match = lookup_dict[key_lower]
                # Update Postcode
                if pd.notna(match.get('postcode')):
                     df_new.at[idx, 'postcode'] = match.get('postcode')
                
                # Update Demographics (if columns exist in v2? They don't yet, need to create)
                for col in keep_cols:
                    if col not in df_new.columns:
                        df_new[col] = None
                    # Only update if master has value
                    if pd.notna(match.get(col)):
                        df_new.at[idx, col] = match.get(col)
                enriched_count += 1
                
    print(f"Enriched {enriched_count} rows using Master Dataset.")
    
    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_new.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved enriched data to {OUTPUT_PATH}")
    
    # Stats
    missing_after = df_new['postcode'].isna().sum()
    print(f"Remaining Missing Postcodes: {missing_after}")
    if missing_after > 0:
        print("Still Missing Brands:")
        print(df_new[df_new['postcode'].isna()]['Brand Name'].value_counts())

if __name__ == "__main__":
    enrich_data()
