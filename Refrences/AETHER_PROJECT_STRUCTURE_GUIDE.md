# Aether Environmental Monitoring Platform
## Complete Data Engineering Project Structure Guide

> **Last Updated**: March 2026  
> **Project Type**: Data Engineering & Machine Learning Platform  
> **Tech Stack**: Python, SQL Server 2019, scikit-learn, Power BI, Streamlit, Task Scheduler

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Complete Directory Structure](#complete-directory-structure)
3. [Detailed Folder Explanations](#detailed-folder-explanations)
4. [Essential Files Breakdown](#essential-files-breakdown)
5. [Setup Instructions](#setup-instructions)
6. [Development Workflow](#development-workflow)
7. [Best Practices](#best-practices)
8. [CI/CD Pipeline](#cicd-pipeline)
9. [Documentation Standards](#documentation-standards)
10. [Production Deployment](#production-deployment)

---

## 🎯 Project Overview

**Aether** is a comprehensive Data Engineering and Machine Learning platform designed to monitor and predict environmental risks related to air quality and urban heat in Cairo, Egypt.

### Key Features:
- ✅ Multi-source data collection (Weather & Air Quality APIs)
- ✅ Automated ETL pipelines with SQL Server integration
- ✅ Feature engineering (Heat Index, Pollution Level)
- ✅ ML-powered daily risk predictions (High/Low)
- ✅ Interactive dashboards (Power BI & Streamlit)
- ✅ Automated daily updates and alerts

### Problem Statement:
Cairo experiences frequent high temperatures and elevated air pollution levels. PM2.5 and PM10 values often exceed WHO safe limits, leading to increased respiratory and cardiovascular health risks. Current monitoring systems lack predictive capabilities.

---

## 📁 Complete Directory Structure

```
aether/
│
├── .github/                          # GitHub-specific files
│   ├── workflows/                    # CI/CD workflows
│   │   ├── ci.yml                   # Continuous Integration
│   │   ├── cd.yml                   # Continuous Deployment
│   │   └── tests.yml                # Automated testing
│   ├── ISSUE_TEMPLATE/              # Issue templates
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   └── PULL_REQUEST_TEMPLATE.md     # PR template
│
├── config/                           # Configuration files
│   ├── __init__.py
│   ├── database.py                  # DB connection configs
│   ├── api_keys.py                  # API key management (not committed)
│   ├── settings.py                  # General settings
│   ├── logging_config.py            # Logging configuration
│   └── config.yaml                  # YAML config file
│
├── data/                             # Data storage (not committed to git)
│   ├── raw/                         # Raw data from sources
│   │   ├── weather/
│   │   │   ├── cairo_weather_YYYYMMDD.csv
│   │   │   └── egypt_precipitation_YYYYMMDD.csv
│   │   └── air_quality/
│   │       ├── global_pollution_YYYYMMDD.csv
│   │       └── urban_aqi_YYYYMMDD.csv
│   ├── processed/                   # Cleaned and transformed data
│   │   ├── weather_cleaned_YYYYMMDD.csv
│   │   └── air_quality_cleaned_YYYYMMDD.csv
│   ├── features/                    # Engineered features
│   │   └── daily_features_YYYYMMDD.csv
│   └── external/                    # Third-party datasets
│       └── who_air_quality_guidelines.csv
│
├── models/                           # Trained ML models
│   ├── saved_models/                # Serialized model files
│   │   ├── risk_prediction_v1.pkl
│   │   ├── risk_prediction_v2.pkl
│   │   └── model_metadata.json
│   ├── checkpoints/                 # Training checkpoints
│   └── evaluation/                  # Model evaluation results
│       ├── confusion_matrices/
│       ├── feature_importance/
│       └── performance_metrics.json
│
├── notebooks/                        # Jupyter notebooks
│   ├── 01_exploratory_data_analysis.ipynb
│   ├── 02_data_cleaning.ipynb
│   ├── 03_feature_engineering.ipynb
│   ├── 04_model_development.ipynb
│   ├── 05_model_evaluation.ipynb
│   └── 06_visualization_prototypes.ipynb
│
├── src/                              # Source code (main package)
│   ├── __init__.py
│   │
│   ├── data_collection/             # Data ingestion modules
│   │   ├── __init__.py
│   │   ├── weather_api.py          # Weather data fetching
│   │   ├── air_quality_api.py      # Air quality data fetching
│   │   ├── data_validator.py       # Input validation
│   │   └── api_client.py           # Generic API client
│   │
│   ├── data_processing/             # ETL and data transformation
│   │   ├── __init__.py
│   │   ├── cleaner.py              # Data cleaning functions
│   │   ├── transformer.py          # Data transformations
│   │   ├── validator.py            # Data quality checks
│   │   └── feature_engineer.py     # Feature engineering
│   │
│   ├── database/                    # Database operations
│   │   ├── __init__.py
│   │   ├── connection.py           # DB connection manager
│   │   ├── queries.py              # SQL queries
│   │   ├── models.py               # ORM models (optional)
│   │   └── migrations/             # Database migrations
│   │       ├── 001_initial_schema.sql
│   │       ├── 002_add_risk_table.sql
│   │       └── migration_manager.py
│   │
│   ├── models/                      # Machine learning models
│   │   ├── __init__.py
│   │   ├── risk_predictor.py       # Main prediction model
│   │   ├── model_trainer.py        # Training pipeline
│   │   ├── model_evaluator.py      # Evaluation metrics
│   │   └── model_registry.py       # Model versioning
│   │
│   ├── pipelines/                   # Data pipelines
│   │   ├── __init__.py
│   │   ├── etl_pipeline.py         # Main ETL orchestration
│   │   ├── training_pipeline.py    # ML training pipeline
│   │   ├── prediction_pipeline.py  # Daily prediction pipeline
│   │   └── pipeline_scheduler.py   # Scheduling logic
│   │
│   ├── visualization/               # Dashboard and reporting
│   │   ├── __init__.py
│   │   ├── streamlit_app.py        # Streamlit dashboard
│   │   ├── powerbi_connector.py    # Power BI data connector
│   │   ├── charts.py               # Chart generation
│   │   └── report_generator.py     # Automated reports
│   │
│   ├── utils/                       # Utility functions
│   │   ├── __init__.py
│   │   ├── logger.py               # Logging utilities
│   │   ├── decorators.py           # Custom decorators
│   │   ├── validators.py           # Validation helpers
│   │   ├── date_utils.py           # Date/time utilities
│   │   └── metrics.py              # Custom metrics
│   │
│   └── alerts/                      # Alert system
│       ├── __init__.py
│       ├── email_alerts.py         # Email notifications
│       ├── sms_alerts.py           # SMS notifications (future)
│       └── alert_manager.py        # Alert orchestration
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── unit/                        # Unit tests
│   │   ├── test_data_collection.py
│   │   ├── test_data_processing.py
│   │   ├── test_feature_engineering.py
│   │   ├── test_models.py
│   │   └── test_utils.py
│   ├── integration/                 # Integration tests
│   │   ├── test_etl_pipeline.py
│   │   ├── test_database.py
│   │   └── test_api_integration.py
│   ├── fixtures/                    # Test data fixtures
│   │   ├── sample_weather_data.csv
│   │   └── sample_air_quality_data.csv
│   └── conftest.py                  # Pytest configuration
│
├── scripts/                          # Standalone scripts
│   ├── setup_database.py            # Database initialization
│   ├── run_daily_update.py          # Daily automation script
│   ├── backfill_data.py             # Historical data backfill
│   ├── deploy.py                    # Deployment script
│   └── health_check.py              # System health check
│
├── dashboards/                       # Dashboard files
│   ├── powerbi/
│   │   ├── aether_dashboard.pbix    # Power BI file
│   │   ├── data_model.json          # Data model config
│   │   └── README.md                # Dashboard documentation
│   └── streamlit/
│       ├── app.py                   # Main Streamlit app
│       ├── pages/                   # Multi-page app
│       │   ├── home.py
│       │   ├── risk_prediction.py
│       │   └── historical_analysis.py
│       └── assets/                  # Static assets
│           ├── logo.png
│           └── styles.css
│
├── docs/                             # Documentation
│   ├── architecture/
│   │   ├── system_design.md         # System architecture
│   │   ├── data_flow.md             # Data flow diagrams
│   │   └── er_diagram.png           # Entity-Relationship diagram
│   ├── api/
│   │   └── api_documentation.md     # API endpoint docs
│   ├── user_guide/
│   │   ├── installation.md          # Installation guide
│   │   ├── user_manual.md           # User manual
│   │   └── troubleshooting.md       # Common issues
│   ├── developer_guide/
│   │   ├── contributing.md          # Contribution guidelines
│   │   ├── code_style.md            # Code style guide
│   │   └── testing.md               # Testing guidelines
│   └── data_dictionary.md           # Data definitions
│
├── sql/                              # SQL scripts
│   ├── schemas/
│   │   ├── create_tables.sql        # Table definitions
│   │   ├── create_views.sql         # View definitions
│   │   └── create_indexes.sql       # Index definitions
│   ├── stored_procedures/
│   │   ├── sp_calculate_risk.sql
│   │   └── sp_generate_report.sql
│   ├── queries/
│   │   ├── daily_summary.sql
│   │   └── trend_analysis.sql
│   └── backups/                     # Backup scripts
│       └── backup_script.sql
│
├── deployment/                       # Deployment configurations
│   ├── docker/
│   │   ├── Dockerfile               # Docker image definition
│   │   ├── docker-compose.yml       # Multi-container setup
│   │   └── .dockerignore
│   ├── kubernetes/                  # K8s configs (if applicable)
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   └── terraform/                   # Infrastructure as Code
│       └── main.tf
│
├── logs/                             # Application logs (not committed)
│   ├── app.log
│   ├── etl_pipeline.log
│   └── errors.log
│
├── reports/                          # Generated reports (not committed)
│   ├── daily/
│   │   └── risk_report_YYYYMMDD.csv
│   └── weekly/
│       └── summary_YYYYMMDD.pdf
│
├── .env.example                      # Environment variables template
├── .env                              # Actual environment variables (NOT COMMITTED)
├── .gitignore                        # Git ignore rules
├── .gitattributes                    # Git attributes
├── .pre-commit-config.yaml           # Pre-commit hooks
├── .editorconfig                     # Editor configuration
│
├── requirements.txt                  # Python dependencies (pip)
├── requirements-dev.txt              # Development dependencies
├── environment.yml                   # Conda environment (alternative)
├── pyproject.toml                    # Project metadata & build config
├── setup.py                          # Package installation script
├── setup.cfg                         # Setup configuration
│
├── Makefile                          # Automation commands
├── pytest.ini                        # Pytest configuration
├── .coveragerc                       # Code coverage config
├── mypy.ini                          # Type checking config
├── .flake8                           # Linting configuration
├── .pylintrc                         # Pylint configuration
│
├── CHANGELOG.md                      # Version history
├── LICENSE                           # License file (MIT recommended)
├── README.md                         # Main project documentation
├── CONTRIBUTING.md                   # Contribution guidelines
├── CODE_OF_CONDUCT.md                # Code of conduct
└── AUTHORS.md                        # Project contributors
```

---

## 📂 Detailed Folder Explanations

### 1. **`.github/`** - GitHub Integration
Contains GitHub-specific automation and templates.

**Why it matters**: Enables automated testing, deployments, and standardized issue/PR workflows.

**Key files**:
- `workflows/ci.yml`: Runs tests on every push/PR
- `workflows/cd.yml`: Deploys to production on merge to main
- `ISSUE_TEMPLATE/`: Guides users to provide necessary information
- `PULL_REQUEST_TEMPLATE.md`: Ensures consistent PR descriptions

### 2. **`config/`** - Configuration Management
Centralized configuration for database connections, API keys, and settings.

**Why it matters**: Separates configuration from code, enables environment-specific settings.

**Best practices**:
- Never commit API keys or passwords
- Use environment variables for sensitive data
- Maintain separate configs for dev/staging/prod

### 3. **`data/`** - Data Storage
Organized storage for raw, processed, and feature-engineered data.

**Why it matters**: Clear data lineage and versioning.

**Structure**:
- `raw/`: Unchanged data from sources (immutable)
- `processed/`: Cleaned and validated data
- `features/`: Engineered features ready for modeling
- `external/`: Third-party reference data

**Important**: Add entire `data/` folder to `.gitignore` (except `.gitkeep` files)

### 4. **`models/`** - Model Artifacts
Stores trained models, checkpoints, and evaluation results.

**Why it matters**: Model versioning, reproducibility, and rollback capability.

**Best practices**:
- Use semantic versioning (v1.0.0, v1.1.0, v2.0.0)
- Store model metadata (training date, hyperparameters, performance)
- Keep production models separate from experimental ones

### 5. **`notebooks/`** - Jupyter Notebooks
Exploratory data analysis, prototyping, and documentation.

**Why it matters**: Interactive exploration and communication with stakeholders.

**Best practices**:
- Use numbered prefixes (01_, 02_) to show workflow sequence
- Clear all outputs before committing
- Add narrative markdown cells explaining findings
- Convert important notebooks to production code in `src/`

### 6. **`src/`** - Source Code (Main Package)
The heart of the project - production-ready, modular code.

**Why it matters**: Clean, testable, maintainable code architecture.

**Module breakdown**:

#### `data_collection/`
- Fetches data from APIs (OpenWeatherMap, AirVisual, etc.)
- Handles API authentication and rate limiting
- Implements retry logic and error handling

#### `data_processing/`
- Cleans raw data (missing values, outliers, duplicates)
- Transforms data types and formats
- Validates data quality
- Engineers features (Heat Index, Pollution Level)

#### `database/`
- Manages SQL Server connections
- Executes queries and stored procedures
- Handles database migrations
- Implements connection pooling

#### `models/`
- Defines ML models (Logistic Regression, Random Forest)
- Training and retraining pipelines
- Model evaluation and metrics
- Model registry for versioning

#### `pipelines/`
- Orchestrates ETL workflows
- Daily automation logic
- Error handling and logging
- Pipeline monitoring

#### `visualization/`
- Streamlit interactive dashboard
- Power BI data connectors
- Automated report generation
- Chart and graph utilities

#### `utils/`
- Logging configuration
- Custom decorators (retry, timing, caching)
- Validation functions
- Date/time utilities

#### `alerts/`
- Email notifications for high-risk days
- SMS alerts (future feature)
- Alert thresholds and rules

### 7. **`tests/`** - Test Suite
Comprehensive testing for code reliability.

**Why it matters**: Prevents bugs, ensures code quality, enables confident refactoring.

**Test types**:
- **Unit tests**: Test individual functions in isolation
- **Integration tests**: Test component interactions
- **Fixtures**: Reusable test data

**Best practices**:
- Aim for >80% code coverage
- Test edge cases and error conditions
- Use mocking for external dependencies

### 8. **`scripts/`** - Automation Scripts
Standalone scripts for common tasks.

**Why it matters**: Simplifies deployment, maintenance, and operations.

**Common scripts**:
- `setup_database.py`: Initialize database schema
- `run_daily_update.py`: Manual trigger for daily pipeline
- `backfill_data.py`: Populate historical data
- `deploy.py`: Automated deployment
- `health_check.py`: Monitor system status

### 9. **`dashboards/`** - Visualization Assets
Dashboard files and configurations.

**Why it matters**: Provides business value through accessible insights.

**Components**:
- **Power BI**: `.pbix` files with data models
- **Streamlit**: Multi-page interactive app

### 10. **`docs/`** - Documentation
Comprehensive project documentation.

**Why it matters**: Onboarding, knowledge sharing, maintenance.

**Sections**:
- **Architecture**: System design, data flows, diagrams
- **API**: Endpoint documentation
- **User Guide**: Installation, usage, troubleshooting
- **Developer Guide**: Contributing, code style, testing

### 11. **`sql/`** - SQL Scripts
Database schema, queries, and stored procedures.

**Why it matters**: Database version control and documentation.

**Organization**:
- `schemas/`: Table, view, and index definitions
- `stored_procedures/`: Reusable SQL logic
- `queries/`: Common analytical queries
- `backups/`: Backup and restore scripts

### 12. **`deployment/`** - Deployment Configurations
Infrastructure and containerization.

**Why it matters**: Reproducible, scalable deployments.

**Technologies**:
- **Docker**: Containerization for consistency
- **Kubernetes**: Orchestration for production scale
- **Terraform**: Infrastructure as Code

### 13. **`logs/`** - Application Logs
Runtime logs for debugging and monitoring.

**Why it matters**: Troubleshooting, auditing, performance monitoring.

**Best practices**:
- Rotate logs daily
- Separate by log level (INFO, WARNING, ERROR)
- Never commit logs to git

### 14. **`reports/`** - Generated Reports
Automated CSV, PDF, and Excel reports.

**Why it matters**: Stakeholder communication and archival.

**Organization**:
- Daily risk predictions
- Weekly summaries
- Monthly trend analyses

---

## 📄 Essential Files Breakdown

### **README.md** - Project Front Page
The most important file in your repository.

```markdown
# Aether Environmental Monitoring Platform

[![CI/CD](https://github.com/username/aether/workflows/CI/badge.svg)]()
[![Coverage](https://codecov.io/gh/username/aether/branch/main/graph/badge.svg)]()
[![License](https://img.shields.io/badge/License-MIT-blue.svg)]()

> Predicting environmental health risks in Cairo through data engineering and machine learning

## 🌍 Overview

Aether monitors air quality and urban heat to predict daily health risks for Cairo residents. 
The platform integrates weather and pollution data, applies machine learning, and delivers 
actionable insights through interactive dashboards.

## ✨ Features

- 📊 Real-time air quality monitoring (PM2.5, PM10, AQI)
- 🌡️ Heat index calculations for urban heat islands
- 🤖 ML-powered daily risk predictions (High/Low)
- 📈 Interactive Power BI and Streamlit dashboards
- ⏰ Automated daily updates
- 📧 Email alerts for high-risk days

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- SQL Server 2019
- pip or conda

### Installation

1. Clone the repository
```bash
git clone https://github.com/username/aether.git
cd aether
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. Initialize database
```bash
python scripts/setup_database.py
```

6. Run the application
```bash
python scripts/run_daily_update.py
```

## 📊 Data Sources

| Data Type | Source | Link |
|-----------|--------|------|
| Weather - Cairo | Kaggle | [Daily Weather Dataset](https://www.kaggle.com/...) |
| Weather - Egypt | Kaggle | [Precipitation Dataset](https://www.kaggle.com/...) |
| Air Pollution | Kaggle | [Global Air Pollution](https://www.kaggle.com/...) |
| Urban Air Quality | Kaggle | [Air Quality Dataset](https://www.kaggle.com/...) |

## 🏗️ Architecture

```
Data Sources → ETL Pipeline → SQL Server → ML Models → Dashboards
                     ↓
                 Feature Engineering
                     ↓
              Daily Predictions
```

For detailed architecture, see [docs/architecture/system_design.md](docs/architecture/system_design.md)

## 🧪 Testing

Run the test suite:
```bash
pytest tests/ -v --cov=src
```

## 📈 Performance

- **Data Processing**: ~5 minutes for daily update
- **Model Prediction**: < 1 second
- **Dashboard Load Time**: < 3 seconds

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📜 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## 👥 Authors

- **Your Name** - *Initial work* - [@yourusername](https://github.com/yourusername)

See [AUTHORS.md](AUTHORS.md) for full list of contributors.

## 🙏 Acknowledgments

- WHO Air Quality Guidelines
- OpenWeatherMap API
- Cairo Environmental Monitoring Department

## 📞 Contact

- Email: your.email@example.com
- Twitter: [@yourhandle](https://twitter.com/yourhandle)
- Project Link: [https://github.com/username/aether](https://github.com/username/aether)
```

### **.gitignore** - Git Exclusions

```gitignore
# Aether Project .gitignore

# ===== Python =====
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environments
venv/
env/
ENV/
.venv/

# Jupyter Notebook
.ipynb_checkpoints
*.ipynb_checkpoints/

# pyenv
.python-version

# Pytest
.pytest_cache/
.coverage
htmlcov/
*.cover
.hypothesis/

# mypy
.mypy_cache/
.dmypy.json
dmyp.json

# ===== Environment Variables =====
.env
.env.local
.env.*.local
*.env
config/api_keys.py

# ===== Databases =====
*.db
*.sqlite3
*.sql.backup
*.mdf
*.ldf

# ===== Data Files =====
data/raw/*
data/processed/*
data/features/*
data/external/*
!data/**/.gitkeep

# CSV, Excel, Parquet
*.csv
*.xlsx
*.xls
*.parquet
*.feather

# ===== Models =====
models/saved_models/*
models/checkpoints/*
!models/**/.gitkeep
*.pkl
*.joblib
*.h5
*.hdf5
*.pt
*.pth

# ===== Logs =====
logs/
*.log
*.log.*

# ===== Reports =====
reports/
*.pdf
*.docx

# ===== OS Files =====
.DS_Store
Thumbs.db
desktop.ini

# ===== IDEs =====
# VSCode
.vscode/
*.code-workspace

# PyCharm
.idea/
*.iml

# Sublime Text
*.sublime-project
*.sublime-workspace

# ===== Power BI =====
*.pbix.tmp

# ===== Temporary Files =====
tmp/
temp/
*.tmp
*.bak
*.swp
*~

# ===== Credentials =====
*credentials*
*secrets*
*password*
*.key
*.pem

# ===== SQL Server =====
*.dacpac
*.bacpac
```

### **.env.example** - Environment Template

```bash
# Aether Configuration
# Copy this file to .env and fill in your actual values

# ===== Database Configuration =====
DB_SERVER=localhost
DB_NAME=aether_db
DB_USER=your_username
DB_PASSWORD=your_password
DB_PORT=1433
DB_DRIVER=ODBC Driver 17 for SQL Server

# ===== API Keys =====
OPENWEATHER_API_KEY=your_openweather_api_key_here
AIRVISUAL_API_KEY=your_airvisual_api_key_here
WAQI_API_TOKEN=your_waqi_token_here

# ===== Application Settings =====
APP_ENV=development  # development, staging, production
LOG_LEVEL=INFO       # DEBUG, INFO, WARNING, ERROR, CRITICAL
DEBUG=True

# ===== Email Configuration (for alerts) =====
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ALERT_EMAIL_TO=recipient@example.com

# ===== Model Settings =====
MODEL_VERSION=v2
MODEL_PATH=models/saved_models/
PREDICTION_THRESHOLD=0.7

# ===== Scheduling =====
DAILY_UPDATE_TIME=06:00
ENABLE_AUTO_RETRAIN=True
RETRAIN_FREQUENCY_DAYS=30

# ===== Feature Flags =====
ENABLE_EMAIL_ALERTS=True
ENABLE_SMS_ALERTS=False
ENABLE_POWER_BI_REFRESH=True
```

### **requirements.txt** - Python Dependencies

```
# Aether Platform Dependencies

# ===== Core Data Processing =====
pandas==2.1.4
numpy==1.26.2
scipy==1.11.4

# ===== Database =====
pyodbc==5.0.1
sqlalchemy==2.0.23
pymssql==2.2.11

# ===== Machine Learning =====
scikit-learn==1.3.2
joblib==1.3.2

# ===== Data Collection =====
requests==2.31.0
python-dotenv==1.0.0
beautifulsoup4==4.12.2

# ===== Visualization =====
streamlit==1.29.0
plotly==5.18.0
matplotlib==3.8.2
seaborn==0.13.0

# ===== Utilities =====
pyyaml==6.0.1
python-dateutil==2.8.2
pytz==2023.3.post1

# ===== Logging & Monitoring =====
loguru==0.7.2

# ===== Task Scheduling =====
apscheduler==3.10.4
schedule==1.2.0

# ===== Email =====
sendgrid==6.11.0

# ===== Testing & Quality =====
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0

# ===== Code Quality =====
black==23.12.1
flake8==6.1.0
mypy==1.7.1
isort==5.13.2
pylint==3.0.3

# ===== Documentation =====
mkdocs==1.5.3
mkdocs-material==9.5.2
```

### **requirements-dev.txt** - Development Dependencies

```
# Development-only dependencies
-r requirements.txt

# ===== Jupyter =====
jupyter==1.0.0
jupyterlab==4.0.9
ipykernel==6.27.1
ipywidgets==8.1.1

# ===== Database Tools =====
sqlfluff==2.3.5

# ===== Profiling =====
memory-profiler==0.61.0
line-profiler==4.1.1

# ===== Pre-commit Hooks =====
pre-commit==3.6.0

# ===== API Documentation =====
sphinx==7.2.6
sphinx-rtd-theme==2.0.0
```

### **setup.py** - Package Installation

```python
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="aether",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Environmental monitoring and risk prediction platform for Cairo",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/username/aether",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Atmospheric Science",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "black>=23.12.1",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "aether-update=src.scripts.run_daily_update:main",
            "aether-dashboard=src.visualization.streamlit_app:main",
        ],
    },
)
```

### **Makefile** - Automation Commands

```makefile
.PHONY: help install test clean lint format run-dashboard run-etl docker-build docker-up

# Default target
help:
	@echo "Aether Platform - Available Commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make test          - Run test suite"
	@echo "  make lint          - Run code linting"
	@echo "  make format        - Format code with black and isort"
	@echo "  make clean         - Remove generated files"
	@echo "  make run-dashboard - Start Streamlit dashboard"
	@echo "  make run-etl       - Run daily ETL pipeline"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-up     - Start Docker containers"

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pip install -e .

test:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

lint:
	flake8 src/ tests/
	mypy src/
	pylint src/

format:
	black src/ tests/ scripts/
	isort src/ tests/ scripts/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ htmlcov/ .pytest_cache/ .mypy_cache/

run-dashboard:
	streamlit run dashboards/streamlit/app.py

run-etl:
	python scripts/run_daily_update.py

setup-db:
	python scripts/setup_database.py

docker-build:
	docker build -t aether:latest -f deployment/docker/Dockerfile .

docker-up:
	docker-compose -f deployment/docker/docker-compose.yml up -d

docker-down:
	docker-compose -f deployment/docker/docker-compose.yml down

ci:
	make lint
	make test

all: clean install test lint
```

### **pytest.ini** - Test Configuration

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

addopts =
    -v
    --strict-markers
    --tb=short
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80

markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow-running tests
    db: Database tests

filterwarnings =
    ignore::DeprecationWarning
```

### **.flake8** - Linting Configuration

```ini
[flake8]
max-line-length = 100
exclude =
    .git,
    __pycache__,
    build,
    dist,
    venv,
    .venv,
    .eggs,
    *.egg-info,
    .tox,
    .pytest_cache,
    .mypy_cache

ignore =
    E203,  # whitespace before ':'
    E501,  # line too long (handled by black)
    W503,  # line break before binary operator

per-file-ignores =
    __init__.py:F401
```

### **mypy.ini** - Type Checking

```ini
[mypy]
python_version = 3.9
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False
disallow_incomplete_defs = True
check_untyped_defs = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True

[mypy-pandas.*]
ignore_missing_imports = True

[mypy-sklearn.*]
ignore_missing_imports = True

[mypy-pyodbc.*]
ignore_missing_imports = True
```

### **CONTRIBUTING.md** - Contribution Guidelines

```markdown
# Contributing to Aether

Thank you for considering contributing to Aether! This document provides guidelines
for contributing to the project.

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to
uphold this code. Please report unacceptable behavior to [email].

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in Issues
2. If not, create a new issue using the bug report template
3. Include:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)

### Suggesting Features

1. Check if the feature has been suggested in Issues
2. Create a new issue using the feature request template
3. Clearly describe the feature and its benefits

### Pull Request Process

1. **Fork the repository** and create a new branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards

3. **Write or update tests** for your changes
   ```bash
   make test
   ```

4. **Ensure code quality**
   ```bash
   make lint
   make format
   ```

5. **Update documentation** if needed

6. **Commit your changes** with clear messages
   ```bash
   git commit -m "Add: Feature XYZ to improve ABC"
   ```

7. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

8. **Create a Pull Request** with:
   - Clear title and description
   - Reference to related issues
   - Screenshots/examples if applicable

## Development Setup

```bash
# Clone the repository
git clone https://github.com/username/aether.git
cd aether

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
make install

# Setup pre-commit hooks
pre-commit install
```

## Coding Standards

### Python Style Guide

- Follow PEP 8
- Use Black for formatting (line length: 100)
- Use type hints where possible
- Write docstrings for all public functions/classes

### Example:

```python
def calculate_heat_index(
    temperature: float,
    humidity: float
) -> float:
    """
    Calculate heat index using temperature and humidity.
    
    Args:
        temperature: Temperature in Celsius
        humidity: Relative humidity (0-100%)
    
    Returns:
        Heat index value in Celsius
    
    Raises:
        ValueError: If inputs are out of valid range
    """
    if not (0 <= humidity <= 100):
        raise ValueError("Humidity must be between 0 and 100")
    
    # Implementation here
    return heat_index
```

### Commit Message Format

```
Type: Brief description (max 50 chars)

Detailed explanation of what and why (if needed)

- Bullet points for multiple changes
- Reference issues with #123

Types: Add, Update, Fix, Remove, Refactor, Docs, Test
```

## Testing Guidelines

- Write unit tests for all new functions
- Aim for >80% code coverage
- Use fixtures for test data
- Mock external dependencies

```python
def test_calculate_heat_index():
    """Test heat index calculation with valid inputs."""
    result = calculate_heat_index(30.0, 70.0)
    assert 32.0 < result < 35.0
```

## Questions?

Feel free to reach out:
- Email: your.email@example.com
- Twitter: @yourhandle
- Discussions: GitHub Discussions tab

Thank you for contributing! 🙏
```

---

## 🚀 Setup Instructions

### Step 1: Initialize Git Repository

```bash
# Create project directory
mkdir aether
cd aether

# Initialize git
git init

# Create initial branch structure
git checkout -b main

# Create .gitignore
# (Copy content from above)

# Make first commit
git add .gitignore
git commit -m "Initial commit: Add .gitignore"
```

### Step 2: Create Directory Structure

```bash
# Create all directories at once
mkdir -p .github/workflows
mkdir -p .github/ISSUE_TEMPLATE
mkdir -p config data/{raw,processed,features,external}
mkdir -p models/{saved_models,checkpoints,evaluation}
mkdir -p notebooks
mkdir -p src/{data_collection,data_processing,database,models,pipelines,visualization,utils,alerts}
mkdir -p tests/{unit,integration,fixtures}
mkdir -p scripts
mkdir -p dashboards/{powerbi,streamlit/pages,streamlit/assets}
mkdir -p docs/{architecture,api,user_guide,developer_guide}
mkdir -p sql/{schemas,stored_procedures,queries,backups}
mkdir -p deployment/{docker,kubernetes,terraform}
mkdir -p logs reports/{daily,weekly}

# Create .gitkeep files to preserve empty directories
find . -type d -empty -exec touch {}/.gitkeep \;
```

### Step 3: Create Initial Files

```bash
# Create __init__.py files for Python packages
find src -type d -exec touch {}/__init__.py \;
find tests -type d -exec touch {}/__init__.py \;

# Create essential config files
touch .env.example .env
touch requirements.txt requirements-dev.txt
touch setup.py Makefile
touch README.md CONTRIBUTING.md LICENSE CHANGELOG.md
touch pytest.ini .flake8 mypy.ini
```

### Step 4: Setup Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install project in editable mode
pip install -e .
```

### Step 5: Configure Environment Variables

```bash
# Copy template
cp .env.example .env

# Edit .env with your actual credentials
nano .env  # or vim, code, etc.
```

### Step 6: Initialize Database

```bash
# Run database setup script
python scripts/setup_database.py

# Verify tables were created
# Connect to SQL Server and check schema
```

### Step 7: Setup Git Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Test hooks
pre-commit run --all-files
```

---

## 💻 Development Workflow

### Daily Development Process

```bash
# 1. Pull latest changes
git pull origin main

# 2. Create feature branch
git checkout -b feature/add-new-data-source

# 3. Make changes and test frequently
python -m pytest tests/

# 4. Format code
make format

# 5. Run linting
make lint

# 6. Commit changes
git add .
git commit -m "Add: New weather data source integration"

# 7. Push to GitHub
git push origin feature/add-new-data-source

# 8. Create Pull Request on GitHub
```

### Code Review Checklist

Before submitting PR, ensure:
- [ ] All tests pass
- [ ] Code coverage >80%
- [ ] No linting errors
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Commit messages are clear
- [ ] No sensitive data in code

---

## ✅ Best Practices

### 1. **Version Control**
- Commit early and often
- Write descriptive commit messages
- Use feature branches
- Never commit sensitive data
- Review code before merging

### 2. **Code Quality**
- Follow PEP 8 style guide
- Write docstrings for all functions/classes
- Use type hints
- Keep functions small and focused
- DRY (Don't Repeat Yourself)

### 3. **Testing**
- Write tests before fixing bugs (TDD)
- Test edge cases and error conditions
- Use meaningful test names
- Mock external dependencies
- Aim for high coverage

### 4. **Documentation**
- Keep README updated
- Document all APIs
- Include code examples
- Maintain architectural diagrams
- Write inline comments for complex logic

### 5. **Data Management**
- Never commit large data files
- Document data sources
- Maintain data lineage
- Version datasets
- Validate data quality

### 6. **Security**
- Use environment variables for secrets
- Never hardcode credentials
- Regularly update dependencies
- Implement proper access controls
- Sanitize user inputs

### 7. **Performance**
- Profile code to find bottlenecks
- Use appropriate data structures
- Implement caching where beneficial
- Optimize database queries
- Monitor resource usage

---

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

**`.github/workflows/ci.yml`**

```yaml
name: CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Lint with flake8
      run: |
        flake8 src/ tests/
    
    - name: Type check with mypy
      run: |
        mypy src/
    
    - name: Run tests with pytest
      run: |
        pytest tests/ -v --cov=src --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  build:
    needs: test
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: |
        docker build -t aether:latest -f deployment/docker/Dockerfile .
```

---

## 📖 Documentation Standards

### Module Docstrings

```python
"""
Data collection module for weather and air quality APIs.

This module provides functions to fetch data from various environmental
monitoring APIs including OpenWeatherMap, AirVisual, and WAQI.

Example:
    >>> from src.data_collection import weather_api
    >>> data = weather_api.fetch_current_weather("Cairo")
    >>> print(data['temperature'])
    32.5

Attributes:
    API_BASE_URL (str): Base URL for weather API
    RETRY_ATTEMPTS (int): Number of retry attempts for failed requests
"""
```

### Function Docstrings

```python
def calculate_pollution_level(
    pm25: float,
    pm10: float,
    aqi: int
) -> str:
    """
    Calculate pollution level category from air quality metrics.
    
    Combines PM2.5, PM10, and AQI values to determine overall pollution
    level according to WHO guidelines.
    
    Args:
        pm25: Fine particulate matter concentration (μg/m³)
        pm10: Coarse particulate matter concentration (μg/m³)
        aqi: Air Quality Index (0-500 scale)
    
    Returns:
        Pollution level category: 'Low', 'Moderate', 'High', or 'Very High'
    
    Raises:
        ValueError: If any input value is negative
        TypeError: If inputs are not numeric
    
    Example:
        >>> calculate_pollution_level(35.5, 68.2, 120)
        'High'
    
    Note:
        Based on WHO Air Quality Guidelines (2021)
    """
```

---

## 🚀 Production Deployment

### Deployment Checklist

- [ ] All tests passing
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Secrets securely stored
- [ ] Monitoring/alerting setup
- [ ] Backup strategy in place
- [ ] Documentation updated
- [ ] Rollback plan prepared

### Docker Deployment

```bash
# Build image
docker build -t aether:v1.0.0 -f deployment/docker/Dockerfile .

# Run container
docker run -d \
  --name aether-app \
  -p 8501:8501 \
  -v /path/to/data:/app/data \
  --env-file .env \
  aether:v1.0.0
```

### Database Migrations

```bash
# Create migration
python -m src.database.migrations.migration_manager create \
  --name "add_risk_score_table"

# Apply migrations
python -m src.database.migrations.migration_manager upgrade

# Rollback migration
python -m src.database.migrations.migration_manager downgrade
```

---

## 📊 Monitoring & Maintenance

### Health Checks

```bash
# Run system health check
python scripts/health_check.py

# Check database connection
python -c "from src.database import connection; connection.test_connection()"

# Verify API accessibility
python -c "from src.data_collection import weather_api; weather_api.health_check()"
```

### Log Monitoring

```bash
# View recent errors
tail -f logs/errors.log

# Search for specific issues
grep "ERROR" logs/app.log | tail -20

# Monitor ETL pipeline
tail -f logs/etl_pipeline.log
```

---

## 🎓 Resources & References

### Documentation
- [Aether Architecture](docs/architecture/system_design.md)
- [API Documentation](docs/api/api_documentation.md)
- [User Manual](docs/user_guide/user_manual.md)

### External Resources
- [Data Engineering Best Practices](https://github.com/josephmachado/data_engineering_best_practices)
- [Cookiecutter Data Science](https://drivendata.github.io/cookiecutter-data-science/)
- [The Twelve-Factor App](https://12factor.net/)

### Tools
- [GitHub](https://github.com)
- [Docker](https://www.docker.com)
- [SQL Server](https://www.microsoft.com/sql-server)
- [Streamlit](https://streamlit.io)
- [Power BI](https://powerbi.microsoft.com)

---

## 📞 Support

For questions, issues, or contributions:

- **GitHub Issues**: [https://github.com/username/aether/issues](https://github.com/username/aether/issues)
- **Email**: your.email@example.com
- **Documentation**: [https://aether.readthedocs.io](https://aether.readthedocs.io)

---

**Last Updated**: March 2026  
**Version**: 1.0.0  
**Maintainer**: Your Name (@yourusername)
