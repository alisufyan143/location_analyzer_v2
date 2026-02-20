
import pandas as pd
from pathlib import Path

INPUT_FILE = Path(r"data/processed/v2_enriched_sales.csv")
OUTPUT_TEMPLATE = Path(r"data/raw/transport_income_template.csv")

def create_transport_template():
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found.")
        return

    print("--- Creating Manual Entry Template for Transport & Income ---")
    df = pd.read_csv(INPUT_FILE)
    
    # We want unique combinations of Postcode and Outercode that are missing data.
    # Transport data depends on postcode. Income depends on outercode.
    
    # Filter rows that are missing transport OR income
    mask_missing = df['Distance_to_Nearest_Station'].isna() | df['avg_household_income'].isna()
    
    df_missing = df[mask_missing]
    
    # Get unique postcodes to ask the user
    # We'll include Brand and Branch Name for context
    unique_locations = df_missing[['Brand Name', 'Branch Name', 'postcode', 'outercode']].drop_duplicates(subset=['postcode'])
    
    # Create Template DataFrame
    template_cols = [
        "Brand Name",
        "Branch Name",
        "postcode", 
        "outercode", 
        "avg_household_income", 
        "Distance_to_Nearest_Station", 
        "Nearby_Station_Count", 
        "Nearest_Station_Type", 
        "Transport_Accessibility_Score",
        "CrystalRoof_URL",
        "PostcodeArea_URL"
    ]
    
    df_template = pd.DataFrame(columns=template_cols)
    
    for col in ["Brand Name", "Branch Name", "postcode", "outercode"]:
        df_template[col] = unique_locations[col].values
        
    # Generate Helper URLs
    # CrystalRoof uses format: https://crystalroof.co.uk/report/postcode/[postcode without space]
    def make_cr_url(pc):
        if pd.isna(pc): return ""
        clean_pc = str(pc).replace(" ", "").upper()
        return f"https://crystalroof.co.uk/report/postcode/{clean_pc}/transport"
        
    # PostcodeArea uses: https://www.postcodearea.co.uk/postaltowns/[town]/[outercode]/
    # We'll just provide the root URL or search URL since town is hard to guess reliably here
    def make_pa_url(oc):
        if pd.isna(oc): return ""
        clean_oc = str(oc).strip().upper()
        # The user can search the outercode on the main page.
        return f"https://www.postcodearea.co.uk/search/?q={clean_oc}"

    df_template['CrystalRoof_URL'] = df_template['postcode'].apply(make_cr_url)
    df_template['PostcodeArea_URL'] = df_template['outercode'].apply(make_pa_url)
    
    # Save the template
    df_template.to_csv(OUTPUT_TEMPLATE, index=False)
    print(f"Created template with {len(df_template)} rows at {OUTPUT_TEMPLATE}")
    print("Columns required: avg_household_income, Distance_to_Nearest_Station, Nearby_Station_Count, Nearest_Station_Type, Transport_Accessibility_Score")

if __name__ == "__main__":
    create_transport_template()
