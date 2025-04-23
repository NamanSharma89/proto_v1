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
- 🔄 Automated nightly data processing pipeline
- 📝 PostgreSQL database integration with proper table relationships
- 🧠 AWS Bedrock integration for advanced language understanding
- 🚀 FastAPI framework for high-performance API endpoints

## 🛠️ Architecture

The system consists of:

1. **Data Processing Layer**: Extract data from Excel and store in a queryable format
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
│   ├── models/                  # Data models
│   └── utils/                   # Utilities
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

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Contributors

- Naman Sharma