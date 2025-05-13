#!/bin/bash
# deploy/terraform/bootstrap.sh

set -e

# Default values
PROJECT_NAME="hospital-data-chatbot"
ENVIRONMENT="dev-cloud"
AWS_REGION="ap-south-1"
AWS_PROFILE="nash-cli-1"

# Help message
function show_help() {
  echo "Usage: $0 [options]"
  echo ""
  echo "Bootstrap Terraform infrastructure for Hospital Data Chatbot"
  echo ""
  echo "Options:"
  echo "  -p, --project-name NAME   Project name (default: hospital-data-chatbot)"
  echo "  -e, --environment ENV     Environment (default: dev-cloud)"
  echo "  -r, --region REGION       AWS region (default: ap-south-1)"
  echo "  --profile PROFILE         AWS profile to use (uses default or SSO session if not specified)"
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
    --profile)
      AWS_PROFILE="$2"
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

# Set AWS profile if specified
if [ -n "$AWS_PROFILE" ]; then
  echo "Using AWS profile: $AWS_PROFILE"
  export AWS_PROFILE="$AWS_PROFILE"
fi

# Detect if we have AWS credentials available
function check_aws_credentials() {
  # First try with get-caller-identity which works with SSO
  if aws sts get-caller-identity >/dev/null 2>&1; then
    return 0
  fi
  
  # If that fails, check if we have credential environment variables
  if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
    return 0
  fi
  
  return 1
}

# Check AWS CLI configuration
echo "Checking AWS CLI configuration..."
if ! check_aws_credentials; then
  echo "Error: No AWS credentials found. Please run 'aws sso login' or set AWS credential environment variables."
  echo "If you're using AWS SSO, make sure to specify the profile with --profile <profile_name>"
  exit 1
fi

# Get the AWS account ID for bucket naming
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
echo "Using AWS Account ID: ${AWS_ACCOUNT_ID}"

# Create S3 bucket for Terraform state
BUCKET_NAME="${PROJECT_NAME}-terraform-state-${ENVIRONMENT}-${AWS_ACCOUNT_ID}"
echo "Creating S3 bucket for Terraform state: ${BUCKET_NAME}"
aws s3 mb s3://${BUCKET_NAME} --region ${AWS_REGION} || {
  echo "Note: S3 bucket may already exist"
}

# Enable versioning on the S3 bucket
echo "Enabling versioning on S3 bucket..."
aws s3api put-bucket-versioning \
  --bucket ${BUCKET_NAME} \
  --versioning-configuration Status=Enabled \
  --region ${AWS_REGION}

# Create DynamoDB table for state locking
DYNAMO_TABLE="${PROJECT_NAME}-terraform-locks-${ENVIRONMENT}"
echo "Creating DynamoDB table for state locking: ${DYNAMO_TABLE}"
aws dynamodb create-table \
  --table-name ${DYNAMO_TABLE} \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ${AWS_REGION} || {
  echo "Note: DynamoDB table may already exist"
}

# Create or update backend config file
BACKEND_DIR="deploy/terraform/environments/backend-config"
mkdir -p ${BACKEND_DIR}

cat > ${BACKEND_DIR}/${ENVIRONMENT}.hcl << EOF
bucket         = "${BUCKET_NAME}"
key            = "${ENVIRONMENT}/terraform.tfstate"
region         = "${AWS_REGION}"
dynamodb_table = "${DYNAMO_TABLE}"
encrypt        = true
EOF

echo "Created backend config file: ${BACKEND_DIR}/${ENVIRONMENT}.hcl"

echo "Bootstrap complete! You can now initialize Terraform:"
echo ""
echo "cd deploy/terraform"
echo "terraform init -backend-config=environments/backend-config/${ENVIRONMENT}.hcl"
echo ""
echo "Then apply the Terraform configuration:"
echo ""
echo "terraform apply -var-file=environments/${ENVIRONMENT}.tfvars -var=\"db_password=YOUR_PASSWORD\""