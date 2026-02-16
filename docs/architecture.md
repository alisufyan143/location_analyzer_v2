# Location Analyzer v2 — Architecture

## Overview

Location Analyzer is a production-grade UK postcode analysis tool that:
1. **Scrapes** demographic, amenity, and transport data from multiple sources
2. **Predicts** sales potential using ML models
3. **Visualizes** results via an interactive web dashboard
4. **Stores** everything in a database with JSON caching

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                    FastAPI (API Layer)               │
│     POST /api/v1/analyze    GET /dashboard/{pc}     │
└──────────────────────┬──────────────────────────────┘
                       │
              ┌────────▼────────┐
              │  Pipeline Layer  │
              │  (Orchestrator)  │
              └───┬────┬────┬───┘
                  │    │    │
   ┌──────────────┤    │    ├──────────────┐
   ▼              ▼    │    ▼              ▼
┌──────┐  ┌────────┐   │  ┌────────┐  ┌──────┐
│Scrape│  │  ML    │   │  │  Viz   │  │ Data │
│Layer │  │Predict │   │  │Web App │  │Layer │
└──┬───┘  └────────┘   │  └────────┘  └──┬───┘
   │                   │                  │
   ▼                   │                  ▼
┌────────────────┐     │        ┌──────────────┐
│ FreeMapTools   │     │        │  PostgreSQL   │
│ StreetCheck    │     │        │  (prod)       │
│ CrystalRoof    │     │        │  SQLite (dev) │
│ Google Maps    │     │        │  JSON Cache   │
└────────────────┘     │        └──────────────┘
                       │
                  ┌────▼────┐
                  │  Models │
                  │  (.pkl) │
                  └─────────┘
```

## Configuration

All configuration is managed via **Pydantic Settings** (`config.py`), loaded from environment variables or `.env` file.

| Setting Group | Prefix | Example |
|---|---|---|
| Database | `DATABASE_` | `DATABASE_URL=postgresql://...` |
| API | `API_` | `API_PORT=8000` |
| Scraper | `SCRAPER_` | `SCRAPER_MAX_DELAY=8.0` |
| ML | `ML_` | `ML_DEFAULT_METRIC=rmse` |
| Paths | (none) | `DATA_DIR=data` |
| Logging | `LOG_` | `LOG_LEVEL=INFO` |

## Error Handling

Custom exception hierarchy under `LocationAnalyzerError`:

```
LocationAnalyzerError
├── ScraperError
│   ├── ScraperBlockedError
│   ├── ScraperTimeoutError
│   ├── ScraperParsingError
│   └── ScraperFallbackExhaustedError
├── DatabaseError
│   ├── DatabaseConnectionError
│   └── PostcodeNotFoundError
├── PredictionError
│   ├── ModelNotFoundError
│   ├── TrainingDataError
│   └── FeatureEngineeringError
└── ValidationError
    └── InvalidPostcodeError
```

## Logging

Structured logging via `logging_config.py`:
- **Console**: `HH:MM:SS | LEVEL | message`
- **File**: `YYYY-MM-DD HH:MM:SS | LEVEL | module:function:line | message`
- Third-party loggers (urllib3, selenium, playwright) suppressed to WARNING
