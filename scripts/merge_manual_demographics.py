
import pandas as pd
from pathlib import Path

# Paths
ENRICHED_DATA_PATH = Path(r"data/processed/v2_enriched_sales.csv")
MANUAL_TEMPLATE_PATH = Path(r"data/raw/demographics_template.csv")
OUTPUT_PATH = Path(r"data/processed/v2_enriched_sales.csv") # Overwrite

def merge_manual_data():
    if not ENRICHED_DATA_PATH.exists():
        print(f"Error: {ENRICHED_DATA_PATH} not found.")
        return
    if not MANUAL_TEMPLATE_PATH.exists():
        print(f"Error: {MANUAL_TEMPLATE_PATH} not found.")
        return

    print("--- Merging Manual Demographics ---")
    
    # Load Data
    df_main = pd.read_csv(ENRICHED_DATA_PATH)
    df_manual = pd.read_csv(MANUAL_TEMPLATE_PATH)
    
    print(f"Main Dataset: {len(df_main)} rows")
    print(f"Manual Data: {len(df_manual)} rows")
    
    # Ensure outercode exists in main (it should from previous steps)
    if 'outercode' not in df_main.columns:
        print("Error: 'outercode' column missing in main dataset.")
        return

    # Helper to standardize outercode
    def clean_code(x):
        return str(x).strip().upper() if pd.notna(x) else None

    # Ensure outercode is populated in main df
    # Some rows (like Galos manual overrides) might have postcode but no outercode yet
    def get_outercode(row):
        if pd.notna(row.get('outercode')):
            return row['outercode']
        if pd.notna(row.get('postcode')):
            return row['postcode'].split()[0].strip()
        # Fallback? No, if no postcode, we can't link unless we merge on Brand?
        return None

    df_main['outercode_clean'] = df_main.apply(get_outercode, axis=1).apply(clean_code)
    df_manual['outercode_clean'] = df_manual['outercode'].apply(clean_code)
    
    # DEBUG
    print("Main Outercodes (Sample):", df_main['outercode_clean'].unique()[:10])
    print("Manual Outercodes:", df_manual['outercode_clean'].unique())
    
    # columns to update
    # The template has: population, households, avg_household_income, unemployment_rate, working_pct, ab_pct, c1_c2_pct, de_pct, white_pct, non_white_pct
    # Main DF expects: population, households, avg_household_income, unemployment_rate, working, unemployed, ab, c1/c2, de, white, non-white
    
    # Map Manual Cols -> Main Cols
    # Note: User might have entered 55% as 55 or 0.55. We need to be careful.
    # Standard: The main dataset uses 0.55 for 55%.
    # Let's inspect the manual data first? No, let's assume user entered regular numbers.
    # Actually, let's print a sample to check format.
    
    # Mapping
    col_map = {
        "population": "population",
        "households": "households",
        "avg_household_income": "avg_household_income",
        "unemployment_rate": "unemployment_rate",
        "working_pct": "working",
        "ab_pct": "ab",
        "c1_c2_pct": "c1/c2",
        "de_pct": "de",
        "white_pct": "white",
        "non_white_pct": "non-white"
    }
    
    # Create a dictionary from manual data for easy lookup
    manual_dict = df_manual.set_index('outercode_clean').to_dict('index')
    
    updated_count = 0
    
    for idx, row in df_main.iterrows():
        oc = row['outercode_clean']
        if oc in manual_dict:
            manual_row = manual_dict[oc]
            
            # Check if main row is missing data (e.g. population is NaN)
            # We overwrite if it matches the 'missing' criteria or just overwrite to be sure?
            # Enriched data has gaps for these outercodes, so overwrite is safe.
            
            for manual_col, main_col in col_map.items():
                val = manual_row.get(manual_col)
                if pd.notna(val):
                    # Data Cleaning/Normalization
                    # If it's a percentage column and value > 1, assume it's 0-100 and divide by 100?
                    # Columns that are percentages: unemployment_rate, working, ab, c1/c2, de, white, non-white
                    pct_cols = ["unemployment_rate", "working", "ab", "c1/c2", "de", "white", "non-white"]
                    
                    final_val = val
                    if main_col in pct_cols:
                        # Simple heuristic: if any value in the whole MANUAL column is > 1.0, treat as percentage
                        # But wait, we are row by row.
                        # Let's rely on type.
                        try:
                            f_val = float(val)
                            # If user entered 50 for 50%, we want 0.50
                            # But what if specific value is small?
                            # Look at strict range? Unemployed rate 5% vs 0.05.
                            # Usually > 1 means %.
                            # But 'working' can be 80%.
                            # Let's assume user followed existing convention or we fix later in EDA.
                            # For safety, let's NOT auto-convert arbitrarily unless obvious > 1.
                            if f_val > 1.0:
                                final_val = f_val / 100.0
                            else:
                                final_val = f_val
                        except:
                            pass
                            
                    df_main.at[idx, main_col] = final_val
            
            updated_count += 1

    # Cleanup
    if 'outercode_clean' in df_main.columns:
        df_main = df_main.drop(columns=['outercode_clean'])
        
    print(f"Merged demographics for {updated_count} rows.")
    
    # Save
    df_main.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved merged dataset to {OUTPUT_PATH}")
    
    # Verify
    missing_pop = df_main['population'].isna().sum()
    print(f"Remaining rows with missing population: {missing_pop}")

if __name__ == "__main__":
    merge_manual_data()
