# Location Analyzer v2

Production-grade UK postcode analysis tool with demographic scraping, ML-powered sales predictions, and interactive web dashboards.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/alisufyan143/location_analyzer_v2.git
cd location_analyzer_v2

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Run tests
python -m pytest tests/ -v

# Start the server
python -m uvicorn src.location_analyzer.api.app:app --port 8000
```

## Project Structure

```
src/location_analyzer/
├── config.py          # Configuration (Pydantic Settings)
├── logging_config.py  # Structured logging
├── exceptions.py      # Custom exception hierarchy
├── api/               # FastAPI endpoints
├── scrapers/          # Web scrapers (FreeMapTools, StreetCheck, CrystalRoof, Google Maps)
├── data/              # Database, ORM models, cache
├── ml/                # ML training, prediction, evaluation
├── visualization/     # Web dashboard
└── pipeline/          # Orchestration
```

## Features

- **Multi-source scraping** with anti-detection and fallback chains
- **10 ML models** trained and compared — auto-selects the best performer
- **Interactive web dashboard** for exploring postcode analysis results
- **PostgreSQL/SQLite** dual-database support
- **Comprehensive testing** per phase

## Documentation

- [Architecture](docs/architecture.md) — system design, config reference
- [API Reference](docs/api.md) — endpoints and usage *(coming in Phase 6)*
- [ML Pipeline](docs/ml_pipeline.md) — model training and evaluation *(coming in Phase 4)*
- [Deployment](docs/deployment.md) — Docker setup *(coming in Phase 7)*

## License

MIT