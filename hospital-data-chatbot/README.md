# 🏥 Hospital Data Chatbot

> An AI-powered chatbot for analyzing hospital patient data using AWS Bedrock and SageMaker

![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Python: 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100.0+-ff69b4)
![Polars](https://img.shields.io/badge/Polars-0.18.0+-orange)

## 📋 Overview

This application provides an intelligent chatbot interface for hospital staff to query patient and diagnosis data through natural language. It uses AWS Bedrock Large Language Models to interpret queries and provides accurate statistics and insights on hospital data.

### Key Features

- 🔍 Natural language query interface for hospital data analysis
- 📊 Accurate statistical calculations on patient metrics
- 🧹 Advanced data sanitization for cleaning special characters and formatting
- 🔄 Automated nightly data processing pipeline
- 📝 PostgreSQL database integration with proper table relationships
- 🧠 AWS Bedrock integration for advanced language understanding
- 🚀 FastAPI framework for high-performance API endpoints

## ✨ Recent Enhancements

- **Robust Data Sanitization**: Added comprehensive data cleaning to remove special characters, normalize whitespace, and ensure consistent formatting
- **Improved Type Safety**: Enhanced validation with consistent string-based comparisons for IDs and other fields
- **Better Error Handling**: Added multiple fallback mechanisms for Excel loading and data processing
- **Enhanced Validation**: Added detailed data quality checks with comprehensive reporting
- **Type Validation**: New validation for data types in both patient and diagnosis records

## 🛠️ Architecture

The system consists of:

1. **Data Processing Layer**: Extract and sanitize data from Excel and store in a queryable format
2. **Model Layer**: AWS Bedrock for LLM access
3. **Business Logic Layer**: Python application to handle queries and calculations
4. **Deployment Layer**: AWS infrastructure for hosting

## 🚀 Getting Started

### Setup with uv (Recommended)

#### Unix/MacOS
```bash
./setup_uv.sh
```

### Traditional Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run locally for testing
python -m app.main
```

## 🧪 Local Testing

### Prerequisites

1. Install a local PostgreSQL instance or use Docker:
   ```bash
   docker run --name postgres-test -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=hospital_data_test -p 5432:5432 -d postgres:14
   ```

2. Create a `.env` file in project root:
   ```
   DEBUG=True
   PORT=8080
   DATA_DIR=data
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=hospital_data_test
   DB_USER=postgres
   DB_PASSWORD=postgres
   USE_S3=False
   ```

3. Prepare test data:
   ```bash
   mkdir -p data/raw
   cp path/to/your/hospital_data.xlsx data/raw/
   ```

4. Launch the API:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
   ```

5. Access the API documentation:
   - http://localhost:8080/docs

## 🌩️ AWS Deployment

```bash
# Build Docker image
docker build -t hospital-chatbot:latest .

# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
docker tag hospital-chatbot:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/hospital-chatbot:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/hospital-chatbot:latest

# Deploy CloudFormation stack
aws cloudformation deploy \
  --template-file deploy/cloudformation.yaml \
  --stack-name hospital-chatbot \
  --parameter-overrides Environment=dev ModelId=anthropic.claude-3-sonnet-20240229-v1:0 \
  --capabilities CAPABILITY_IAM
```

## 📚 Data Processing Features

### Data Sanitization

The application includes advanced data sanitization features:

- **Column-Specific Rules**: Different sanitization rules for IDs, names, and medical terminology
- **Special Character Handling**: Removes unwanted special characters while preserving important punctuation
- **Whitespace Normalization**: Trims extra spaces and standardizes formatting
- **Detailed Reporting**: Tracks modified cells and provides sanitization statistics

### Data Validation

Comprehensive data validation ensures data integrity:

- **Orphaned Record Detection**: Identifies diagnosis records without matching patients
- **Duplicate Detection**: Finds duplicate patient IDs with consistent type handling
- **Type Validation**: Validates numeric fields, dates, and categorical values
- **Missing Value Detection**: Identifies records with missing critical information

## 🔒 AWS Security Configuration

### IAM Roles

Create a role with permissions for:
- ✅ Bedrock access
- ✅ S3 access for data storage
- ✅ CloudWatch for logging

### Data Security

- 🔐 Encrypt hospital data at rest in S3
- 🛡️ Use VPC endpoints for secure communication
- 🔑 Implement proper authentication for API access

## 📂 Project Structure

```
hospital-data-chatbot/
│
├── app/                         # Application code
│   ├── api/                     # API endpoints
│   ├── config/                  # Configuration
│   ├── core/                    # Core logic
│   │   ├── data_processor.py    # Enhanced data processing and sanitization
│   │   ├── llm_connector.py     # AWS Bedrock LLM interface
│   │   └── query_engine.py      # Natural language query processing
│   ├── models/                  # Data models
│   └── utils/                   # Utilities
│       ├── db.py                # Database utilities
│       └── calculation_handler.py # Statistical calculation handling
│
├── data/                        # Data files
│   ├── raw/                     # Original data
│   └── processed/               # Processed data
│
├── deploy/                      # Deployment files
│   └── cloudformation.yaml      # AWS CloudFormation template
│
├── tests/                       # Unit tests
│
├── scripts/                     # Utility scripts
│   └── nightly_import.py        # Nightly data import
│
├── Dockerfile                   # Container definition
├── pyproject.toml               # Project dependencies
├── setup.py                     # Package setup
└── README.md                    # This file
```

## 🚀 Future Enhancements

- 💾 Add Caching: Cache common queries for faster responses
- 🧠 Implement Vector Database: Store embeddings for semantic search capabilities
- 🖥️ Build a Web Interface: Create a simple UI for interacting with the chatbot
- 🔐 Add Authentication: Secure the API with proper user authentication
- 📊 Enhanced Visualizations: Add graphical representation of query results
- 🔄 Real-time Data Updates: Support for real-time data updates beyond nightly batch processing
- 🧪 Comprehensive Test Suite: Add unit and integration tests for all components

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Contributors

- Naman Sharma