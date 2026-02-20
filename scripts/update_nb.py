import json
import os

NB_PATH = r"d:\work\automation\free_map_tools\final\Location_analyzer\location_analyzer_v2\notebooks\Machine_Learning_Pipeline.ipynb"

try:
    with open(NB_PATH, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    # Update cell 0
    nb['cells'][0]['source'] = [
        "# Location Analyzer v2 - Machine Learning Pipeline\n",
        "\n",
        "## 1. Setup & Data Loading\n",
        "We will analyze `v3_master_combined.csv` which contains both Historical and Prediction data."
    ]

    # Update cell 1
    new_data_path = 'r"D:\\work\\automation\\free_map_tools\\final\\Location_analyzer\\location_analyzer_v2\\data\\processed\\v3_master_combined.csv"'
    nb['cells'][1]['source'] = [
        "import pandas as pd\n",
        "import numpy as np\n",
        "import matplotlib.pyplot as plt\n",
        "import seaborn as sns\n",
        "import os\n",
        "\n",
        "# Pandas display options\n",
        "pd.set_option('display.max_columns', None)\n",
        "pd.set_option('display.width', 1000)\n",
        "\n",
        "# Define file path\n",
        f"DATA_PATH = {new_data_path}\n",
        "\n",
        "print(f\"Loading data from: {DATA_PATH}\")"
    ]

    # Update cell 2 (read_csv instead of read_excel)
    nb['cells'][2]['source'] = [
        "# Load the dataset\n",
        "try:\n",
        "    df = pd.read_csv(DATA_PATH, low_memory=False)\n",
        "    print(\"Data loaded successfully!\")\n",
        "    print(f\"Shape: {df.shape}\")\n",
        "except Exception as e:\n",
        "    print(f\"Error loading data: {e}\")"
    ]

    def create_markdown_cell(source):
        return {
            "cell_type": "markdown",
            "metadata": {},
            "source": [l + "\n" for l in source]
        }

    def create_code_cell(source):
        return {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [l + "\n" for l in source]
        }

    new_cells = [
        create_markdown_cell(["## 4. Data Cleaning"]),
        create_code_cell([
            "# 4.1 Separate Historical vs Prediction Data",
            "# We only want to evaluate and drop targets on Historical Data.",
            "df_hist = df[df['Dataset'] == 'Historical'].copy()",
            "df_pred = df[df['Dataset'] == 'Prediction'].copy()",
            "print(f\"Historical shape: {df_hist.shape}\")",
            "print(f\"Prediction shape: {df_pred.shape}\")"
        ]),
        create_code_cell([
            "# 4.2 Drop Missing Targets (Total Sale) from Historical",
            "initial_len = len(df_hist)",
            "df_hist = df_hist.dropna(subset=['Total Sale'])",
            "dropped = initial_len - len(df_hist)",
            "print(f\"Dropped {dropped} rows with missing Total Sale in Historical data.\")",
            "print(f\"New Historical shape: {df_hist.shape}\")"
        ]),
        create_code_cell([
            "# 4.3 Recombine for Joint Feature Engineering/Imputation",
            "df_clean = pd.concat([df_hist, df_pred], ignore_index=True)",
            "print(f\"Cleaned Combined shape: {df_clean.shape}\")"
        ]),
        create_code_cell([
            "# 4.4 Fix Invalid Zeros",
            "cols_to_check = ['population', 'households', 'avg_household_income', 'unemployment_rate', ",
            "                 'working', 'unemployed', 'ab', 'c1/c2', 'de', 'white', 'non-white']",
            "for col in cols_to_check:",
            "    # Replace 0s with NaN so the imputer can handle them",
            "    zero_count = (df_clean[col] == 0).sum()",
            "    if zero_count > 0:",
            "        df_clean.loc[df_clean[col] == 0, col] = np.nan",
            "        print(f\"Replaced {zero_count} zeros with NaN in {col}\")"
        ])
    ]

    # Check if cells exist
    existing_sources = [cell['source'][0].strip() if cell.get('source') else '' for cell in nb['cells']]
    if '## 4. Data Cleaning' not in existing_sources:
        nb['cells'].extend(new_cells)

    with open(NB_PATH, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

    print("Notebook updated successfully.")

except Exception as e:
    print(f"Error updating notebook: {e}")
