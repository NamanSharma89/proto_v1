#!/bin/bash

# terraform-infra-manager.sh - A script to manage AWS infrastructure with Terraform
# Author: Claude

# Set script to exit on error
set -e

# Default values
TF_DIR="./terraform"
ENV="dev"
COMMAND=""
APPLY_ARGS=""
DESTROY_ARGS=""
VERBOSE=false

# Function to display usage information
function show_usage() {
    echo "Usage: $0 [OPTIONS] COMMAND"
    echo ""
    echo "A utility script to manage Terraform infrastructure"
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
    echo ""
    echo "Options:"
    echo "  -d, --directory DIR   Terraform directory (default: ./terraform)"
    echo "  -e, --environment ENV Environment to deploy (dev, staging, prod)"
    echo "  -a, --auto-approve    Skip interactive approval for apply/destroy"
    echo "  -v, --verbose         Show detailed output"
    echo "  -h, --help            Display this help message"
    echo ""
    echo "Examples:"
    echo "  $0 init                         # Initialize Terraform"
    echo "  $0 -e prod apply                # Deploy to production"
    echo "  $0 -a destroy                   # Destroy infra without confirmation"
    echo "  $0 -e staging -a all            # Full deployment to staging"
    echo ""
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
        -h|--help)
            show_usage
            exit 0
            ;;
        init|plan|apply|destroy|output|validate|workspace|fmt|all)
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
if [ ! -d "$TF_DIR" ]; then
    echo "Error: Terraform directory '$TF_DIR' does not exist."
    echo "Create it or specify a different directory with -d option."
    exit 1
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
    
    echo "⚙️  Running: terraform $cmd $args"
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
        run_terraform "init" "-reconfigure"
        ;;
    plan)
        run_terraform "plan" "$TF_VAR_FILE"
        ;;
    apply)
        run_terraform "apply" "$TF_VAR_FILE $APPLY_ARGS"
        ;;
    destroy)
        echo "⚠️  WARNING: This will destroy all resources in the $ENV environment! ⚠️"
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
        run_terraform "init" "-reconfigure" && \
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