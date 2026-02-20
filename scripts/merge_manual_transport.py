import pandas as pd
from pathlib import Path

# Paths
ENRICHED_DATA_PATH = Path(r"data/processed/v2_enriched_sales.csv")
MANUAL_TEMPLATE_PATH = Path(r"data/raw/transport_income_template.csv")
OUTPUT_PATH = Path(r"data/processed/v2_enriched_sales.csv")

def main():
    print("--- Merging Manual Transport Data ---")
    
    # Check if files exist
    if not ENRICHED_DATA_PATH.exists() or not MANUAL_TEMPLATE_PATH.exists():
        print("Error: Missing required files.")
        return
        
    df_main = pd.read_csv(ENRICHED_DATA_PATH)
    df_manual = pd.read_csv(MANUAL_TEMPLATE_PATH)
    
    print(f"Main Dataset: {len(df_main)} rows")
    print(f"Manual Data: {len(df_manual)} rows")
    
    # Columns to update
    cols_to_update = [
        'Distance_to_Nearest_Station', 
        'Nearby_Station_Count', 
        'Nearest_Station_Type', 
        'Transport_Accessibility_Score', 
        'avg_household_income'
    ]
    
    # The manual dataset might have empty values where the user couldn't find data (e.g. avg_household_income)
    # We only want to map values that are not null in the manual template
    df_manual_subset = df_manual[['postcode'] + cols_to_update].copy()
    
    for col in cols_to_update:
        # Create a mapping dictionary for non-null values
        valid_manual = df_manual_subset.dropna(subset=[col])
        if not valid_manual.empty:
            mapping = valid_manual.set_index('postcode')[col].to_dict()
            
            # Identify missing rows in main for this column
            is_missing = df_main[col].isna()
            
            # Map values and fill
            df_main.loc[is_missing, col] = df_main.loc[is_missing, 'postcode'].map(mapping)
        
    print(f"Merged transport and income data.")
    
    df_main.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved merged dataset to {OUTPUT_PATH}")
    
    missing_transport = len(df_main[df_main['Distance_to_Nearest_Station'].isna()])
    missing_income = len(df_main[df_main['avg_household_income'].isna()])
    print(f"Remaining rows with missing transport: {missing_transport}")
    print(f"Remaining rows with missing income: {missing_income}")

if __name__ == "__main__":
    main()
