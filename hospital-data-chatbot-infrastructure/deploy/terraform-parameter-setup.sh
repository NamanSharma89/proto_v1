#!/bin/bash
# setup-ssm-parameters.sh

# This script pre-populates SSM Parameter Store with secrets

# Set default values
PROJECT_NAME="hospital-data-chatbot"
ENVIRONMENT="dev-cloud"
AWS_REGION="ap-south-1"
AWS_PROFILE="nash-cli-1"

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
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Set AWS profile
if [ -n "$AWS_PROFILE" ]; then
  export AWS_PROFILE="$AWS_PROFILE"
fi

echo "Setting up SSM Parameter Store for ${PROJECT_NAME} (${ENVIRONMENT})"

# Prompt for the database password
read -s -p "Enter database password: " DB_PASSWORD
echo ""

# Create the SSM Parameter
PARAM_NAME="/${PROJECT_NAME}/${ENVIRONMENT}/db-password"
echo "Creating SSM Parameter: ${PARAM_NAME}"

aws ssm put-parameter \
  --name "${PARAM_NAME}" \
  --description "Database password for ${PROJECT_NAME} ${ENVIRONMENT}" \
  --type "SecureString" \
  --value "${DB_PASSWORD}" \
  --overwrite \
  --region "${AWS_REGION}"

echo "SSM Parameter created successfully."
echo ""
echo "You can now run Terraform without needing to specify the password."
echo "Make sure to set the 'db_password_parameter_name' variable to '${PARAM_NAME}'"