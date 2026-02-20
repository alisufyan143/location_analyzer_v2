import pandas as pd
from pathlib import Path

V1_PATH = Path("data/raw/v1_2025_06/sales_data.xlsx")
V2_PATH = Path("data/processed/v2_enriched_sales.csv")
OUTPUT_PATH = Path("data/processed/v3_master_combined.csv")

def main():
    print("--- Merging V1 (Historical) and V2 (Prediction) Data ---")
    
    # Check
    if not V1_PATH.exists() or not V2_PATH.exists():
        print("Error: Missing required files.")
        return
        
    df_v1 = pd.read_excel(V1_PATH)
    df_v2 = pd.read_csv(V2_PATH)
    
    print(f"V1 shape: {df_v1.shape}")
    print(f"V2 shape: {df_v2.shape}")
    
    # Ensure they have a label (so we can separate them later)
    df_v1['Dataset'] = 'Historical'
    df_v2['Dataset'] = 'Prediction'
    
    # Drop the temporary join columns from v2
    cols_to_drop = ['Join_Branch', 'Join_Key', 'Master_Branch_Match']
    df_v2 = df_v2.drop(columns=[c for c in cols_to_drop if c in df_v2.columns], errors='ignore')
    
    # Combine
    df_combined = pd.concat([df_v1, df_v2], ignore_index=True)
    print(f"Combined shape: {df_combined.shape}")
    
    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_combined.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved combined master dataset to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
