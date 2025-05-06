#!/bin/bash
# deploy/terraform/bootstrap.sh

set -e

# Default values
PROJECT_NAME="hospital-data-chatbot"
ENVIRONMENT="dev_cloud"
AWS_REGION="ap-south-1"

# Help message
function show_help() {
  echo "Usage: $0 [options]"
  echo ""
  echo "Bootstrap Terraform infrastructure for Hospital Data Chatbot"
  echo ""
  echo "Options:"
  echo "  -p, --project-name NAME   Project name (default: hospital-data-chatbot)"
  echo "  -e, --environment ENV     Environment (default: dev_cloud)"
  echo "  -r, --region REGION       AWS region (default: ap-south-1)"
  echo "  -h, --help                Show this help message"
  echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--project-name)
      PROJECT_NAME="$2"
      shift 2
      ;;
    -e|--environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    -r|--region)
      AWS_REGION="$2"
      shift 2
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      show_help
      exit 1
      ;;
  esac
done

echo "Bootstrapping Terraform for ${PROJECT_NAME} (${ENVIRONMENT}) in ${AWS_REGION}"

# Check AWS CLI configuration
echo "Checking AWS CLI configuration..."
aws sts get-caller-identity > /dev/null || {
  echo "Error: AWS CLI not configured properly"
  exit 1
}

# Create S3 bucket for Terraform state
echo "Creating S3 bucket for Terraform state..."
aws s3 mb s3://${PROJECT_NAME}-terraform-state-${ENVIRONMENT} --region ${AWS_REGION} || {
  echo "Note: S3 bucket may already exist"
}

# Enable versioning on the S3 bucket
echo "Enabling versioning on S3 bucket..."
aws s3api put-bucket-versioning \
  --bucket ${PROJECT_NAME}-terraform-state-${ENVIRONMENT} \
  --versioning-configuration Status=Enabled \
  --region ${AWS_REGION}

# Create DynamoDB table for state locking
echo "Creating DynamoDB table for state locking..."
aws dynamodb create-table \
  --table-name ${PROJECT_NAME}-terraform-locks-${ENVIRONMENT} \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ${AWS_REGION} || {
  echo "Note: DynamoDB table may already exist"
}

echo "Bootstrap complete! You can now initialize Terraform:"
echo ""
echo "cd deploy/terraform"
echo "./init.sh ${ENVIRONMENT}"
echo ""
echo "Then apply the Terraform configuration:"
echo ""
echo "terraform apply -var-file=environments/${ENVIRONMENT}.tfvars -var=\"db_password=YOUR_PASSWORD\""