import joblib
import os
import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class PredictionService:
    """
    Loads the trained XGBoost model and all associated Scikit-Learn feature 
    engineering transformers to provide real-time sales predictions.
    """
    
    def __init__(self, model_dir: str):
        self.model_dir = model_dir
        self.model = None
        self.qt = None
        self.kbd = None
        self.pt = None
        self.rs = None
        self.oe = None
        self._load_artifacts()

    def _load_artifacts(self):
        """Loads all .pkl artifacts from the models directory."""
        try:
            model_path = os.path.join(self.model_dir, "xgboost_sales_model_v2_20_2_2026.pkl")
            if not os.path.exists(model_path):
                # Fallback to the original v2 if the specific date one doesn't exist
                model_path = os.path.join(self.model_dir, "xgboost_sales_model_v2.pkl")
                
            self.model = joblib.load(model_path)
            logger.info(f"Successfully loaded XGBoost model from {model_path}")
            
            # Load transformers safely (they will be None if they don't exist)
            transformers = {
                'qt': 'quantile_transformer.pkl',
                'kbd': 'kbins_discretizer.pkl',
                'pt': 'power_transformer.pkl',
                'rs': 'robust_scaler.pkl',
                'oe': 'ordinal_encoder.pkl'
            }
            
            for attr_name, filename in transformers.items():
                path = os.path.join(self.model_dir, filename)
                if os.path.exists(path):
                    setattr(self, attr_name, joblib.load(path))
                    logger.debug(f"Loaded {filename}")
                else:
                    logger.warning(f"Transformer {filename} not found. Ensure it was exported from Notebook.")
                    
        except Exception as e:
            logger.error(f"Failed to load ML artifacts: {e}")
            raise RuntimeError(f"Failed to initialize PredictionService: {e}")

    def _apply_feature_engineering(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Replicates the exact Feature Engineering pipeline from Section 5 of the Jupyter Notebook.
        """
        df_clean = df.copy()
        df_clean = df_clean.astype(float, errors='ignore')

        # 1. Population Capping (OOD Fix)
        if 'population' in df_clean.columns:
            df_clean['population'] = df_clean['population'].clip(lower=30000)

        # 2. Log1p Transformations
        log_cols = ['population', 'households', 'Distance_to_Nearest_Station']
        for col in log_cols:
            if col in df_clean.columns:
                # Convert to float to avoid dtype mapping issues
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
                df_clean[col] = np.log1p(df_clean[col])

        # 3. Sqrt Transformations
        if 'Nearby_Station_Count' in df_clean.columns:
            df_clean['Nearby_Station_Count'] = pd.to_numeric(df_clean['Nearby_Station_Count'], errors='coerce')
            df_clean['Nearby_Station_Count'] = np.sqrt(df_clean['Nearby_Station_Count'])

        # 4. QuantileTransformer (non-white)
        if 'non-white' in df_clean.columns and self.qt is not None:
            mask = df_clean['non-white'].notna()
            df_clean['non-white_quantile'] = np.nan
            if mask.sum() > 0:
                values = df_clean.loc[mask, ['non-white']]
                df_clean.loc[mask, 'non-white_quantile'] = self.qt.transform(values)

        # 5. KBinsDiscretizer (unemployed, ab, de)
        kmeans_cols = ['unemployed', 'ab', 'de']
        if self.kbd is not None:
            # Note: kbd expects these 3 columns together in the same order as fitted
            # We must pass the df chunk that has these columns
            available_cols = [c for c in kmeans_cols if c in df_clean.columns]
            if len(available_cols) > 0:
                # Find rows where ALL required columns are not null for the transform
                mask = df_clean[available_cols].notna().all(axis=1)
                
                # Initialize the new columns with NaN
                for col in available_cols:
                    df_clean[f'{col}_kmeans_bin'] = np.nan
                    
                if mask.sum() > 0:
                    try:
                        # kbd.transform expects the exact same columns it was fitted on.
                        # We must pull out exactly the columns it trained on.
                        transformed = self.kbd.transform(df_clean.loc[mask, available_cols])
                        for idx, col in enumerate(available_cols):
                            df_clean.loc[mask, f'{col}_kmeans_bin'] = transformed[:, idx]
                    except Exception as e:
                        logger.warning(f"Error applying KBinsDiscretizer: {e}")

        # 6. Yeo-Johnson (working, c1/c2)
        yeo_cols = ['working', 'c1/c2']
        if self.pt is not None:
            available_cols = [c for c in yeo_cols if c in df_clean.columns]
            if len(available_cols) > 0:
                mask = df_clean[available_cols].notna().all(axis=1)
                if mask.sum() > 0:
                    try:
                        transformed = self.pt.transform(df_clean.loc[mask, available_cols])
                        for idx, col in enumerate(available_cols):
                            df_clean.loc[mask, col] = transformed[:, idx]
                    except Exception as e:
                        logger.warning(f"Error applying PowerTransformer: {e}")

        # 7. RobustScaler (avg_household_income)
        if 'avg_household_income' in df_clean.columns and self.rs is not None:
            mask = df_clean['avg_household_income'].notna()
            if mask.sum() > 0:
                df_clean.loc[mask, 'avg_household_income'] = self.rs.transform(df_clean.loc[mask, ['avg_household_income']])

        # 8. Suspicious Zeros flag
        if 'unemployment_rate' in df_clean.columns:
            df_clean['unemployment_rate_is_missing'] = df_clean['unemployment_rate'].isna().astype(int)

        # 9. OrdinalEncoder (Transport_Accessibility_Score)
        if 'Transport_Accessibility_Score' in df_clean.columns and self.oe is not None:
            mask = df_clean['Transport_Accessibility_Score'].notna()
            if mask.sum() > 0:
                df_clean.loc[mask, 'Transport_Accessibility_Score'] = self.oe.transform(df_clean.loc[mask, ['Transport_Accessibility_Score']])

        # 10. Date Extractions
        if 'Date' in df_clean.columns:
            df_clean['Date'] = pd.to_datetime(df_clean['Date'], errors='coerce', format='mixed')
            df_clean['Year'] = df_clean['Date'].dt.year
            df_clean['Month'] = df_clean['Date'].dt.month
            df_clean['Dayofweek'] = df_clean['Date'].dt.dayofweek
            df_clean['Is_Weekend'] = df_clean['Dayofweek'].apply(lambda x: 1 if x >= 5 else 0)
        else:
            # Default to today if Date isn't provided in the API call
            from datetime import datetime
            now = datetime.now()
            df_clean['Year'] = now.year
            df_clean['Month'] = now.month
            df_clean['Dayofweek'] = now.weekday()
            df_clean['Is_Weekend'] = 1 if now.weekday() >= 5 else 0

        # Construct final ordered XGBoost DataFrame
        expected_features = self.model.feature_names_in_
        for f in expected_features:
            if f not in df_clean.columns:
                df_clean[f] = np.nan
        
        df_final = df_clean[expected_features].copy()

        # Convert specific columns to native Pandas Categorical specifically for XGBoost
        cat_features = ['Day_of_Week', 'Nearest_Station_Type']
        for col in cat_features:
            if col in df_final.columns:
                # Cast through string to prevent float indices from np.nan injection,
                # then explicitly back to category with actual NaN handling
                cat_col = df_final[col].astype(str).replace('nan', np.nan).astype('category')
                if len(cat_col.cat.categories) == 0:
                    cat_col = cat_col.cat.add_categories(['Missing'])
                df_final[col] = cat_col

        # Convert remaining object columns to float to avoid generic native typing errors
        for col in df_final.columns:
            if df_final[col].dtype == 'object' and col not in cat_features:
                 df_final[col] = pd.to_numeric(df_final[col], errors='coerce')

        return df_final

    def predict(self, raw_data: List[Dict[str, Any]]) -> List[float]:
        """
        Receives raw unscaled data dictionaries, applies all feature engineering, 
        and returns the actual predicted £ sales.
        """
        if not raw_data:
            return []

        df_raw = pd.DataFrame(raw_data)
        
        # 1. Feature Engineer
        df_processed = self._apply_feature_engineering(df_raw)
        
        # 2. Predict (outputs in Log-Space)
        log_preds = self.model.predict(df_processed)
        
        # 3. Transform back to Real £ Sales and clip minimum to £0
        sales_preds = np.expm1(log_preds)
        sales_preds = np.clip(sales_preds, a_min=0, a_max=None)
        
        return sales_preds.tolist()

