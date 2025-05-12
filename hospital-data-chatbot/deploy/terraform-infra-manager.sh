#!/bin/bash

# terraform-infra-manager.sh - A script to manage AWS infrastructure with Terraform
# Enhanced with SSM Parameter Store integration for secure handling of database passwords

# Set script to exit on error
set -e

# Default values
TF_DIR="./terraform"
ENV="dev-cloud"
COMMAND=""
APPLY_ARGS=""
DESTROY_ARGS=""
VERBOSE=false

# Set your default AWS profile here
DEFAULT_AWS_PROFILE="nash-cli-1"  # <-- Set your existing profile name here
AWS_PROFILE=${AWS_PROFILE:-$DEFAULT_AWS_PROFILE}

# Function to display usage information
function show_usage() {
    echo "Usage: $0 [OPTIONS] COMMAND"
    echo ""
    echo "A utility script to manage Terraform infrastructure with secure parameter handling"
    echo ""
    echo "Commands:"
    echo "  init        Initialize Terraform working directory"
    echo "  plan        Generate and show an execution plan"
    echo "  apply       Build or change infrastructure"
    echo "  destroy     Destroy previously-created infrastructure"
    echo "  output      Show output values from your root module"
    echo "  validate    Check whether the configuration is valid"
    echo "  workspace   Switch between workspaces"
    echo "  fmt         Reformat your configuration in the standard style"
    echo "  all         Run init, validate, plan, and apply in sequence"
    echo "  params      Manage SSM parameters (create/update database password)"
    echo ""
    echo "Options:"
    echo "  -d, --directory DIR   Terraform directory (default: ./terraform)"
    echo "  -e, --environment ENV Environment to deploy (dev-cloud, staging, prod)"
    echo "  -a, --auto-approve    Skip interactive approval for apply/destroy"
    echo "  -v, --verbose         Show detailed output"
    echo "  -h, --help            Display this help message"
    echo "  --profile PROFILE     AWS profile to use (default: $DEFAULT_AWS_PROFILE)"
    echo ""
    echo "Examples:"
    echo "  $0 init                         # Initialize Terraform"
    echo "  $0 -e prod apply                # Deploy to production"
    echo "  $0 -a destroy                   # Destroy infra without confirmation"
    echo "  $0 -e staging -a all            # Full deployment to staging"
    echo "  $0 -e dev-cloud params          # Manage database password parameter"
    echo ""
}

# Function to set up AWS profile
function setup_aws_profile() {
    export AWS_PROFILE="$AWS_PROFILE"
    echo "Using AWS profile: $AWS_PROFILE"
    
    # Verify the profile works
    if aws sts get-caller-identity &>/dev/null; then
        echo "✅ AWS profile verified successfully"
        aws sts get-caller-identity --query "Account" --output text
    else
        echo "❌ AWS profile verification failed"
        echo "Please check that your AWS profile '$AWS_PROFILE' is configured correctly"
        exit 1
    fi
}

# Function to check if S3 bucket exists
function check_s3_bucket_exists() {
    local bucket_name="$1"
    local region="$2"
    
    # Use head-bucket command to check if bucket exists and we have access to it
    if aws s3api head-bucket --bucket "$bucket_name" --region "$region" 2>/dev/null; then
        return 0  # Bucket exists and we have access
    else
        return 1  # Bucket doesn't exist or we don't have access
    fi
}

# Function to check if SSM parameter exists (fixed version)
function check_ssm_parameter_exists() {
    local param_name="/$PROJECT_NAME/$BUCKET_ENV/db-password"
    
    if aws ssm get-parameter --name "$param_name" --region "$AWS_REGION" &>/dev/null; then
        echo "DEBUG: Parameter $param_name exists"  # Add debugging
        return 0  # Parameter exists
    else
        echo "DEBUG: Parameter $param_name does not exist"  # Add debugging
        return 1  # Parameter doesn't exist
    fi
}

# Function to create/update database password parameter
function manage_db_password_parameter() {
    local param_name="/$PROJECT_NAME/$BUCKET_ENV/db-password"
    
    echo "Managing SSM Parameter: $param_name"
    
    if check_ssm_parameter_exists; then
        echo "Parameter already exists. Do you want to update it?"
        select yn in "Yes" "No"; do
            case $yn in
                Yes ) break;;
                No ) return 0;;
            esac
        done
    fi
    
    echo "Enter a secure password for the database (will not be shown on screen):"
    read -s DB_PASSWORD
    echo ""
    
    # Confirm password
    echo "Confirm the password:"
    read -s DB_PASSWORD_CONFIRM
    echo ""
    
    if [[ "$DB_PASSWORD" != "$DB_PASSWORD_CONFIRM" ]]; then
        echo "❌ Passwords do not match. Please try again."
        return 1
    fi
    
    # Create/update the parameter (using default AWS encryption)
    if aws ssm put-parameter --name "$param_name" \
        --description "Database password for $PROJECT_NAME $BUCKET_ENV" \
        --type "SecureString" \
        --value "$DB_PASSWORD" \
        --overwrite \
        --region "$AWS_REGION"; then
        
        echo "✅ Parameter $param_name created/updated successfully"
    else
        echo "❌ Failed to create/update parameter $param_name"
        return 1
    fi
    
    return 0
}

# Function to ensure database password parameter exists before terraform operations
function ensure_db_password_parameter() {
    local param_name="/$PROJECT_NAME/$BUCKET_ENV/db-password"
    
    echo "Checking for database password parameter: $param_name"
    
    # Use the aws CLI directly to check for parameter existence
    if aws ssm get-parameter --name "$param_name" --region "$AWS_REGION" &>/dev/null; then
        echo "✅ Database password parameter found in SSM Parameter Store"
        return 0
    else
        echo "⚠️ Database password parameter not found in SSM Parameter Store"
        echo "You need to create this parameter before running Terraform operations"
        
        read -p "Do you want to create the parameter now? (y/n): " CREATE_PARAM
        if [[ "$CREATE_PARAM" =~ ^[Yy]$ ]]; then
            manage_db_password_parameter
            if [ $? -ne 0 ]; then
                echo "❌ Parameter creation failed. Cannot proceed."
                exit 1
            fi
        else
            echo "❌ Cannot proceed without database password parameter"
            echo "You can create it later using: $0 -e $ENV params"
            exit 1
        fi
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -d|--directory)
            TF_DIR="$2"
            shift 2
            ;;
        -e|--environment)
            ENV="$2"
            shift 2
            ;;
        -a|--auto-approve)
            APPLY_ARGS="-auto-approve"
            DESTROY_ARGS="-auto-approve"
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        init|plan|apply|destroy|output|validate|workspace|fmt|all|params)
            COMMAND="$1"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if command is provided
if [ -z "$COMMAND" ]; then
    echo "Error: No command specified."
    show_usage
    exit 1
fi

# Check if terraform directory exists
if [ ! -d "$TF_DIR" ] && [ "$COMMAND" != "params" ]; then
    echo "Error: Terraform directory '$TF_DIR' does not exist."
    echo "Create it or specify a different directory with -d option."
    exit 1
fi

# Set up AWS profile
setup_aws_profile

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
echo "AWS Account ID: $AWS_ACCOUNT_ID"

# Get AWS region
AWS_REGION=$(aws configure get region --profile "$AWS_PROFILE" || echo "ap-south-1")
echo "AWS Region: $AWS_REGION"

# Sanitize environment name (replace underscores with hyphens)
BUCKET_ENV=$(echo ${ENV} | tr '_' '-' | tr '[:upper:]' '[:lower:]')
PROJECT_NAME=$(basename $(pwd) | tr '_' '-' | tr '[:upper:]' '[:lower:]')
if [ -z "$PROJECT_NAME" ] || [ "$PROJECT_NAME" == "." ]; then
    PROJECT_NAME="hospital-data-chatbot"
fi

# Handle the 'params' command separately
if [ "$COMMAND" == "params" ]; then
    echo "🔑 Managing SSM Parameters for $PROJECT_NAME in $ENV environment"
    echo "======================================================"
    manage_db_password_parameter
    echo "======================================================"
    echo "✨ Parameter management completed for environment: $ENV"
    exit 0
fi

# Construct bucket name following the same pattern as bootstrap.sh
BUCKET_NAME="${PROJECT_NAME}-terraform-state-${BUCKET_ENV}-${AWS_ACCOUNT_ID}"
echo "S3 bucket name: $BUCKET_NAME"

# Check if S3 bucket exists
if check_s3_bucket_exists "$BUCKET_NAME" "$AWS_REGION"; then
    echo "✅ S3 bucket '$BUCKET_NAME' exists and is accessible"
    S3_BUCKET_EXISTS=true
else
    echo "⚠️ S3 bucket '$BUCKET_NAME' does not exist or is not accessible"
    
    # Ask if user wants to create it
    read -p "Do you want to create the S3 bucket? (y/n): " CREATE_BUCKET
    if [[ "$CREATE_BUCKET" =~ ^[Yy]$ ]]; then
        echo "Creating S3 bucket: $BUCKET_NAME"
        aws s3 mb s3://$BUCKET_NAME --region $AWS_REGION
        
        echo "Enabling versioning on S3 bucket..."
        aws s3api put-bucket-versioning \
          --bucket $BUCKET_NAME \
          --versioning-configuration Status=Enabled \
          --region $AWS_REGION
        
        S3_BUCKET_EXISTS=true
    else
        echo "⚠️ Cannot proceed without S3 bucket for Terraform state"
        exit 1
    fi
fi

# Check for DynamoDB table
DYNAMO_TABLE="${PROJECT_NAME}-terraform-locks-${BUCKET_ENV}"
if aws dynamodb describe-table --table-name "$DYNAMO_TABLE" --region "$AWS_REGION" &>/dev/null; then
    echo "✅ DynamoDB table '$DYNAMO_TABLE' exists and is accessible"
    DYNAMO_TABLE_EXISTS=true
else
    echo "⚠️ DynamoDB table '$DYNAMO_TABLE' does not exist or is not accessible"
    
    # Ask if user wants to create it
    read -p "Do you want to create the DynamoDB table for state locking? (y/n): " CREATE_TABLE
    if [[ "$CREATE_TABLE" =~ ^[Yy]$ ]]; then
        echo "Creating DynamoDB table: $DYNAMO_TABLE"
        aws dynamodb create-table \
          --table-name $DYNAMO_TABLE \
          --attribute-definitions AttributeName=LockID,AttributeType=S \
          --key-schema AttributeName=LockID,KeyType=HASH \
          --billing-mode PAY_PER_REQUEST \
          --region $AWS_REGION
        
        DYNAMO_TABLE_EXISTS=true
    else
        echo "⚠️ Warning: Proceeding without DynamoDB table for state locking"
        echo "Multiple users may modify infrastructure simultaneously, which could cause conflicts"
    fi
fi

# Ensure backend config directory exists
BACKEND_DIR="$TF_DIR/environments/backend-config"
mkdir -p "$BACKEND_DIR"

# Create or update backend config
if [ "$S3_BUCKET_EXISTS" = true ]; then
    # Create backend config with or without DynamoDB table
    if [ "$DYNAMO_TABLE_EXISTS" = true ]; then
        cat > "$BACKEND_DIR/${ENV}.hcl" << EOF
bucket         = "${BUCKET_NAME}"
key            = "${ENV}/terraform.tfstate"
region         = "${AWS_REGION}"
dynamodb_table = "${DYNAMO_TABLE}"
encrypt        = true
EOF
    else
        cat > "$BACKEND_DIR/${ENV}.hcl" << EOF
bucket         = "${BUCKET_NAME}"
key            = "${ENV}/terraform.tfstate"
region         = "${AWS_REGION}"
encrypt        = true
EOF
    fi
    
    echo "✅ Created/updated backend config: $BACKEND_DIR/${ENV}.hcl"
fi

# For commands that modify infrastructure, ensure the SSM parameter exists
if [[ "$COMMAND" == "apply" || "$COMMAND" == "all" ]]; then
    ensure_db_password_parameter
fi

# Change to terraform directory
cd "$TF_DIR"

# Configure logging based on verbosity
if [ "$VERBOSE" = true ]; then
    export TF_LOG="DEBUG"
else
    export TF_LOG="ERROR"
fi

# Set environment-specific variables file
TF_VAR_FILE=""
if [ -f "environments/${ENV}.tfvars" ]; then
    TF_VAR_FILE="-var-file=environments/${ENV}.tfvars"
    echo "Using environment config: environments/${ENV}.tfvars"
fi

# Set backend configuration if available
BACKEND_CONFIG=""
if [ -f "environments/backend-config/${ENV}.hcl" ]; then
    BACKEND_CONFIG="-backend-config=environments/backend-config/${ENV}.hcl"
    echo "Using backend config: environments/backend-config/${ENV}.hcl"
fi

# Function to calculate elapsed time
function timer() {
    if [[ $# -eq 0 ]]; then
        echo $(date '+%s')
    else
        local start_time=$1
        local end_time=$(date '+%s')
        local elapsed=$((end_time - start_time))
        local mins=$((elapsed / 60))
        local secs=$((elapsed % 60))
        echo "Time elapsed: ${mins}m ${secs}s"
    fi
}

# Execute terraform commands
function run_terraform() {
    local cmd="$1"
    local args="$2"
    
    echo "⚙️ Running: terraform $cmd $args"
    start_time=$(timer)
    
    # Execute the command
    if ! terraform $cmd $args; then
        echo "❌ Terraform $cmd failed!"
        return 1
    fi
    
    echo "✅ Terraform $cmd completed successfully."
    timer $start_time
    echo ""
    return 0
}

# Main execution
echo "🚀 Starting Terraform operations for environment: $ENV"
echo "======================================================"

case "$COMMAND" in
    init)
        INIT_ARGS=""
        if [ -n "$BACKEND_CONFIG" ]; then
            INIT_ARGS="$BACKEND_CONFIG -reconfigure"
        else
            INIT_ARGS="-reconfigure"
        fi
        run_terraform "init" "$INIT_ARGS"
        ;;
    plan)
        # For plan, we want to check if the DB parameter exists but not require it
        if ! check_ssm_parameter_exists; then
            echo "⚠️ Warning: Database password parameter not found in SSM Parameter Store"
            echo "This may cause the plan to fail if your infrastructure uses it."
            echo "Consider running '$0 -e $ENV params' to set up the parameter."
            echo ""
            read -p "Do you want to continue anyway? (y/n): " CONTINUE
            if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
                echo "Operation aborted."
                exit 0
            fi
        fi
        run_terraform "plan" "$TF_VAR_FILE"
        ;;
    apply)
        ensure_db_password_parameter
        run_terraform "apply" "$TF_VAR_FILE $APPLY_ARGS"
        ;;
    destroy)
        echo "⚠️ WARNING: This will destroy all resources in the $ENV environment! ⚠️"
        if [ -z "$DESTROY_ARGS" ]; then
            read -p "Are you absolutely sure? Type 'yes' to confirm: " confirm
            if [ "$confirm" != "yes" ]; then
                echo "Destruction aborted."
                exit 0
            fi
        fi
        run_terraform "destroy" "$TF_VAR_FILE $DESTROY_ARGS"
        ;;
    output)
        run_terraform "output" ""
        ;;
    validate)
        run_terraform "validate" ""
        ;;
    workspace)
        echo "Available workspaces:"
        terraform workspace list
        read -p "Enter workspace name to switch to (or 'new' to create): " workspace
        if [ "$workspace" = "new" ]; then
            read -p "Enter new workspace name: " new_workspace
            run_terraform "workspace new" "$new_workspace"
        else
            run_terraform "workspace select" "$workspace"
        fi
        ;;
    fmt)
        run_terraform "fmt" "-recursive"
        ;;
    all)
        echo "🔄 Running full deployment pipeline..."
        
        # Check for required SSM parameter before starting deployment
        ensure_db_password_parameter
        
        INIT_ARGS=""
        if [ -n "$BACKEND_CONFIG" ]; then
            INIT_ARGS="$BACKEND_CONFIG -reconfigure"
        else
            INIT_ARGS="-reconfigure"
        fi
        
        run_terraform "init" "$INIT_ARGS" && \
        run_terraform "validate" "" && \
        run_terraform "plan" "$TF_VAR_FILE" && \
        run_terraform "apply" "$TF_VAR_FILE $APPLY_ARGS"
        
        # Check if all commands succeeded
        if [ $? -eq 0 ]; then
            echo "🎉 Full deployment completed successfully!"
            run_terraform "output" ""
        else
            echo "❌ Deployment pipeline failed."
            exit 1
        fi
        ;;
    *)
        echo "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac

echo "======================================================"
echo "✨ Operation completed for environment: $ENV"

# Return to original directory
cd - > /dev/null