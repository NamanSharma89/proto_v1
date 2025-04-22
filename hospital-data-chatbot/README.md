# Hospital Data Chatbot
An AI-powered chatbot for analyzing hospital patient data using AWS Bedrock and SageMaker.

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run locally for testing
python -m app.main

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

# Future Enhancements
Add Caching: Cache common queries for faster responses
Implement Vector Database: Store embeddings for semantic search capabilities
Build a Web Interface: Create a simple UI for interacting with the chatbot
Add Authentication: Secure the API with proper user authentication
AWS Setup and Security

IAM Roles: Create a role with permissions for:

Bedrock access
S3 access for data storage
CloudWatch for logging


Data Security:

Encrypt hospital data at rest in S3
Use VPC endpoints for secure communication
Implement proper authentication for API access
