
import pandas as pd
from pathlib import Path

INPUT_FILE = Path(r"data/processed/v2_enriched_sales.csv")
OUTPUT_TEMPLATE = Path(r"data/raw/demographics_template.csv")

def create_template():
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found.")
        return

    print("--- Creating Manual Entry Template ---")
    df = pd.read_csv(INPUT_FILE)
    
    # Logic to identify missing rows (same as scraper)
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
    
    print(f"Found {len(target_outercodes)} unique outercodes needing data.")
    
    # Create Template DataFrame
    template_cols = [
        "outercode", 
        "population", 
        "households", 
        "avg_household_income", 
        "unemployment_rate", 
        "working_pct", # renamed for clarity (decimal or pct?) assume pct for user input? NO, consistent with Schema. 
                       # Schema uses 'working' (float), 'unemployed' (float). 
                       # Let's use user-friendly headers and convert later? 
                       # Stick to Schema for simplicity.
        "ab_pct", "c1_c2_pct", "de_pct", 
        "white_pct", "non_white_pct"
    ]
    
    df_template = pd.DataFrame(target_outercodes, columns=["outercode"])
    
    # Add empty columns
    for col in template_cols[1:]:
        df_template[col] = None
        
    df_template.to_csv(OUTPUT_TEMPLATE, index=False)
    print(f"Created template with {len(df_template)} rows at {OUTPUT_TEMPLATE}")
    print("Columns required: " + ", ".join(template_cols))

if __name__ == "__main__":
    create_template()
