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
