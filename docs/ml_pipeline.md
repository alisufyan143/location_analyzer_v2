# Machine Learning Pipeline (Phase 4)

## Overview
The ML pipeline predicts sales potential for a given location based on demographic, competitive, and amenity data. It is designed to be **interactive** (via Notebooks) for experimentation and **production-ready** (via strict export artifacts).

## Workflow

1.  **Data Ingestion**
    *   **Source**: Consolidated Excel files (Sales + Demographics).
    *   **Cleaning**: Handling missing values, standardizing columns.

2.  **Feature Engineering**
    *   **Imputation**: Mean/Median for numericals, constant for categoricals.
    *   **Encoding**: Target Encoding or OHE for categorical features (e.g., `Nearest_Station_Type`).
    *   **Scaling**: Standard scaling for linear models (not strictly needed for Trees but good practice).

3.  **Model Selection**
    *   **Primary**: XGBoost / CatBoost (GPU Accelerated).
    *   **Baseline**: Random Forest, Linear Regression.
    *   **Strategy**: Train all, compare CV scores, select best.

4.  **Artifacts**
    *   `model.pkl`: The trained model object.
    *   `preprocessor.pkl`: The exact transformation pipeline used during training.
    *   `metrics.json`: Final performance report.

## Directory Structure
*   `notebooks/model_training.ipynb`: The "lab bench" for training.
*   `src/ml/predict.py`: The "factory floor" for serving predictions.
