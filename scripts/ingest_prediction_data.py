
import os
import re
import pandas as pd
from pathlib import Path

# Setup
ROOT_DIR = Path(r"Dataset/Prediction Data")
OUTPUT_PATH = Path(r"data/raw/v2_ingested_sales.csv")

# Regex for Postcode: Flexible whitespace
# Matches "IG1 2RT", "IG1 2 RT", "SW1A 1AA", etc.
POSTCODE_RE = re.compile(r'([Gg][Ii][Rr] 0[Aa]{2})|((([A-Za-z][0-9]{1,2})|(([A-Za-z][A-Ha-hJ-Yj-y][0-9]{1,2})|(([A-Za-z][0-9][A-Za-z])|([A-Za-z][A-Ha-hJ-Yj-y][0-9][A-Za-z]?))))\s*[0-9]\s*[A-Za-z]{2})')

def normalize_postcode(pc):
    """Normalize postcode to uppercase with single space."""
    if not pc or pd.isna(pc):
        return None
    match = POSTCODE_RE.search(str(pc))
    if match:
        return match.group(0).upper().strip()
    return None

def ingest_data():
    print("--- Starting Prediction Data Ingestion (Stage 1) ---")
    
    all_records = []
    
    print(f"Scanning {ROOT_DIR}...")
    for root, dirs, files in os.walk(ROOT_DIR):
        for file in files:
            if not (file.lower().endswith('.xls') or file.lower().endswith('.xlsx')):
                continue
            
            # print(f"Found {file}")
            path = Path(root) / file
            brand_folder = path.parent.parent.name
            
            # Identify Group
            # Group A: Maemes, Rios (Address in Row 0)
            is_group_a = brand_folder in ["Maemes", "Rios"]
            
            print(f"DEBUG: Checking {file} | Brand: {brand_folder} | Group A: {is_group_a}")
            
            try:
                # 1. Metadata Extraction
                # Read first few rows for header info
                df_meta = pd.read_excel(path, header=None, nrows=5)
                row0_val = str(df_meta.iloc[0, 0]) if not df_meta.empty else ""
                
                postcode = None
                branch_name = file.replace(".xls", "").replace(".xlsx", "")
                
                if is_group_a:
                    # Strategy: Extract Postcode from first 5 rows (Header block)
                    for i in range(min(5, len(df_meta))):
                        # Construct a search string from the first 2 columns of this row
                        parts = []
                        if df_meta.shape[1] > 0: parts.append(str(df_meta.iloc[i, 0]))
                        if df_meta.shape[1] > 1: parts.append(str(df_meta.iloc[i, 1]))
                        row_val = " ".join(parts)
                            
                        pc_match = POSTCODE_RE.search(row_val)
                        if pc_match:
                            postcode = normalize_postcode(pc_match.group(0))
                            break # Found it
                    
                    # Clean Branch Name (Cosmetic)
                    clean_branch = branch_name
                    for prefix in ["Maeme's - ", "Maemes - ", "Rio's Piri Piri - ", "Rios Piri Piri - "]:
                        if clean_branch.startswith(prefix):
                            clean_branch = clean_branch.replace(prefix, "")
                    branch_name = clean_branch.strip()
                    # Remove common suffixes like " (Sheldon)" -> "Sheldon" if needed, but sticking to filename is safer for now
                else:
                    # Strategy: Others (Grillo, etc) - No Address
                    branch_name = "Main" # Or use folder name?
                    postcode = None
                
                # 2. Sales Data Extraction - DYNAMIC HEADER DETECTION
                # Read first 10 rows to find the header
                df_preview = pd.read_excel(path, header=None, nrows=10)
                
                header_idx = -1
                date_col_name = ""
                sale_col_name = ""
                
                for idx, row in df_preview.iterrows():
                    # Convert row to string to search for keywords
                    row_str = " ".join([str(x) for x in row.values if pd.notna(x)])
                    
                    if is_group_a and idx < 5:
                         print(f"  [DEBUG Group A] Row {idx}: {row_str}")

                    if "Date" in row_str and ("Total Sale" in row_str or "Amount" in row_str):
                        header_idx = idx
                        # Identify specific column names from this row
                        for col_idx, val in enumerate(row.values):
                            val_str = str(val).strip()
                            if "Date" in val_str:
                                date_col_name = val_str
                            if "Total Sale" in val_str or "Amount" in val_str:
                                sale_col_name = val_str
                        break
                
                if header_idx == -1:
                    print(f"Skipping {file}: Could not find header row with 'Date' and 'Sale/Amount'")
                    continue
                
                if is_group_a:
                    print(f"  [DEBUG Group A] Found Header at Index {header_idx}")

                # Read data starting from the row AFTER the header
                # pd.read_excel(header=N) uses row N as header.
                df_data = pd.read_excel(path, header=header_idx)
                
                if is_group_a:
                     print(f"  [DEBUG Group A] Data Rows: {len(df_data)} | Columns: {df_data.columns.tolist()}")

                # Normalize Columns found dynamically
                df_data.columns = [str(c).strip() for c in df_data.columns]
                
                date_col = next((c for c in df_data.columns if "Date" in c), None)
                sale_col = next((c for c in df_data.columns if "Total Sale" in c or "Amount" in c), None)
                
                if not date_col or not sale_col:
                    print(f"Skipping {file}: Header found at {header_idx} but columns missing. Found {df_data.columns.tolist()}")
                    continue
                    
                for row_idx, row in df_data.iterrows():
                    date_val = row[date_col]
                    sale_val = row[sale_col]
                    
                    if pd.isna(date_val) or pd.isna(sale_val):
                        continue
                        
                    # 3. Build Record
                    record = {
                        "Date": date_val,
                        "Brand Name": brand_folder, # Keeping consistent with master naming
                        "Branch Name": branch_name,
                        "Total Sale": sale_val,
                        "postcode": postcode,
                        "outercode": postcode.split()[0] if postcode else None,
                        "source": "Prediction_Data_v2",
                        "shopname": branch_name, # Normalized branch
                        "Day_of_Week": None # Will calc later or now? Pandas can do it easily
                    }
                    all_records.append(record)
                    
            except Exception as e:
                print(f"Error processing {file}: {e}")

    # Convert to DataFrame
    df = pd.DataFrame(all_records)
    
    # Convert to DataFrame
    df = pd.DataFrame(all_records)
    
    # Post-processing
    if not df.empty:
        # print(f"DEBUG: DataFrame shape before date parse: {df.shape}")
        
        print(f"DEBUG: DataFrame shape before date parse: {df.shape}")
        
        # Clean whitespace first
        df["Date"] = df["Date"].astype(str).str.strip()

        # Filter out garbage rows (e.g. "Total")
        df = df[df["Date"].str.lower() != "total"]

        # Date Parsing Strategy
        # 1. Try default parsing (handles Excel serials, ISO, etc.)
        date_parsed = pd.to_datetime(df["Date"], errors='coerce')
        
        # 2. Identify failures
        mask_nat = date_parsed.isna()
        
        # 3. Try explicit format '%d-%b-%Y' (e.g., 01-Sep-2025) for failures
        if mask_nat.any():
            print(f"DEBUG: Attempting fallback parsing for {mask_nat.sum()} rows...")
            # We explicitly target the rows that failed
            df_retry = df.loc[mask_nat, "Date"]
            date_parsed.loc[mask_nat] = pd.to_datetime(df_retry, format='%d-%b-%Y', errors='coerce')
            
        df["Date"] = date_parsed
        
        # Check for remaining NaT
        failed_dates = df[df["Date"].isna()]
        if not failed_dates.empty:
            print(f"WARNING: {len(failed_dates)} rows still failed date parsing!")
            print(failed_dates[["Date", "Brand Name", "Branch Name"]].head())
        
        df = df.dropna(subset=["Date"])
        df["Day_of_Week"] = df["Date"].dt.strftime("%a")
        
        # Drop debug col
        if "Date_Raw" in df.columns:
            df = df.drop(columns=["Date_Raw"])
        
        # Save
        df.to_csv(OUTPUT_PATH, index=False)
        print(f"Success! Saved {len(df)} rows to {OUTPUT_PATH}")
        
        # Stats
        print("\n--- Ingestion Stats ---")
        print(f"Total Rows: {len(df)}")
        print(f"Unique Postcodes: {df['postcode'].nunique()}")
        print(f"Missing Postcodes: {df['postcode'].isna().sum()}")
        if df['postcode'].isna().sum() > 0:
            print("Brands with Missing Postcodes:")
            print(df[df['postcode'].isna()]['Brand Name'].value_counts())
    else:
        print("No data ingested!")

if __name__ == "__main__":
    ingest_data()
