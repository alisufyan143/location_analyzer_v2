# 📍 Location Analyzer v2

> **Production-grade UK postcode analysis tool powering strategic business decisions.**
> Features demographic scraping, advanced ML sales prediction, and an interactive web dashboard.

---

## 🚀 Overview

**Location Analyzer v2** is a robust Python application designed to evaluate the commercial potential of UK postcodes. By aggregating data from multiple demographic sources (Census, Crime, Affluence) and combining it with proprietary sales data, it uses an **Ensemble Machine Learning Pipeline** to predict future branch performance with high accuracy.

### Key Capabilities
*   **🕷️ Resilient Scraping Architecture**: Multi-source data aggregation (FreeMapTools, StreetCheck, CrystalRoof, Google Maps) with anti-detection layers (proxy rotation, user-agent pooling).
*   **🤖 Advanced ML Pipeline**: Trains and competes 10+ models (XGBoost, LightGBM, CatBoost, etc.) to find the optimal predictor.
*   **📊 Interactive Dashboard**: A modern web interface (FastAPI + Bokeh) to visualize demographic clusters, sales trends, and competitor proximity.
*   **🛡️ Production Ready**: Dockerized deployment, dual-database support (PostgreSQL/SQLite), and comprehensive testing.

---

## 🛠️ Architecture

The project follows a clean, modular architecture designed for maintainability and scale.

```text
src/location_analyzer/
├── api/               # ⚡ FastAPI Service (REST endpoints)
├── data/              # 🗄️ Database Layer (SQLAlchemy + Pydantic)
├── ml/                # 🧠 ML Core (Training, Prediction, Evaluation)
├── pipeline/          # ⚙️ Orchestration (ETL + Analysis Workflows)
├── scrapers/          # 🕸️ Scraper Framework (Playwright + Requests)
└── visualization/     # 📈 Dashboard Engine (Bokeh + Jinja2)
```

---

## 🏁 Quick Start

### Prerequisites
*   Python 3.10+
*   Chrome/Chromium (for Playwright scrapers)
*   PostgreSQL (optional for Prod, SQLite used by default)

### Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/alisufyan143/location_analyzer_v2.git
    cd location_analyzer_v2
    ```

2.  **Set up environment**
    ```bash
    python -m venv venv
    venv\Scripts\activate  # Windows
    # source venv/bin/activate  # Mac/Linux
    
    pip install -e ".[dev]"
    playwright install chromium
    ```

3.  **Configure secrets**
    ```bash
    cp .env.example .env
    # Edit .env with your API keys and Proxy settings
    ```

4.  **Run the analysis**
    ```bash
    # Run the API server
    python -m uvicorn src.location_analyzer.api.app:app --reload --port 8000
    ```

    Visit `http://localhost:8000/docs` for the API definition or `http://localhost:8000/dashboard` for the analytics UI.

---

## 📦 Data & ML Strategy

### Dataset Versioning
We use a structured directory approach to track raw and processed data versions.

```text
data/
├── raw/
│   ├── v1_2025_06/        # Historical data (Up to June 2025)
│   └── v2_2026_01/        # Current rollout (Up to Jan 2026)
└── processed/
    └── v2/                # Training artifacts for the current model
```

### Preprocessing Pipeline
To ensure robust model performance across diverse UK geographies, we apply model-specific transformations:
*   **Log1p Transform**: For right-skewed magnitudes (Population, Total Sales).
*   **Yeo-Johnson**: For left-skewed distributions.
*   **Quantile Binning**: For multimodal demographic features (Social Grades, Ethnicity).
*   **Robust Scaling**: To handle extreme income outliers.

---

## 🧪 Testing

The project maintains high code quality through a rigorous testing suite.

```bash
# Run all tests
python -m pytest tests/ -v

# Run only scraper tests (slow)
python -m pytest tests/test_scrapers/ -v

# Run ML pipeline tests
python -m pytest tests/test_ml/ -v
```

---

## 📜 Documentation

*   [**System Architecture**](docs/architecture.md) – Detailed design doc.
*   [**API Reference**](docs/api.md) – Endpoints and schemas.
*   [**Preprocessing Strategy**](preprocessing_strategy.md) – In-depth data handling logic.

---

## ⚖️ License

Distributed under the MIT License. See `LICENSE` for more information.