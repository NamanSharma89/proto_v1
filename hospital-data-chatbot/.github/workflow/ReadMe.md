# Hospital Data Chatbot CI/CD Pipeline Documentation

This document describes the CI/CD pipeline for the Hospital Data Chatbot project, which uses GitHub Actions and Terraform for infrastructure provisioning and application deployment.

## Pipeline Overview

The CI/CD pipeline consists of the following stages:

1. **Test**: Run unit tests, linting, and code quality checks
2. **Terraform**: Provision or update infrastructure with Terraform
3. **Build and Push**: Build and push Docker image to ECR
4. **Deploy Application**: Deploy the application using ECS Fargate

## Environments

The pipeline supports three environments:

- **Development (dev_cloud)**: Used for development and testing
- **Staging (stage)**: Used for pre-production testing
- **Production (prod)**: Used for production deployment

## Pipeline Triggers

The pipeline is triggered by:

- **Push to main branch**: Automatically deploys to production
- **Push to develop branch**: Automatically deploys to development
- **Manual trigger**: Can deploy to any environment via GitHub Actions UI

## Pipeline Stages

### 1. Test Stage

- Sets up Python environment with the `uv` package manager
- Installs dependencies and development tools
- Runs linting with flake8, black, and isort
- Runs unit tests with pytest and uploads coverage report

### 2. Terraform Stage

- Sets up Terraform with the specified version
- Determines the target environment
- Initializes Terraform with the correct backend configuration
- Validates the Terraform configuration
- Plans the infrastructure changes
- Applies the infrastructure changes
- Outputs important resource identifiers for use in later stages

### 3. Build and Push Stage

- Configures AWS credentials
- Logs in to Amazon ECR
- Builds the Docker image with environment-specific variables
- Tags the image with the commit SHA and environment name
- Pushes the Docker image to ECR

### 4. Deploy Application Stage

- Re-initializes Terraform to ensure up-to-date state
- Applies the application deployment configuration
- Updates the ECS service with the new Docker image
- Verifies the deployment was successful by checking the application health endpoint

## CI/CD Best Practices

The pipeline follows these best practices:

- **Infrastructure as Code**: All infrastructure is defined as code using Terraform
- **Environment Isolation**: Each environment has its own isolated infrastructure
- **Automated Testing**: All code changes are tested before deployment
- **Immutable Infrastructure**: Infrastructure is updated through Terraform, not manual changes
- **Continuous Integration**: Code changes are automatically tested and deployed
- **Continuous Deployment**: Successful changes to the main branch are automatically deployed to production
- **Rollback Capability**: Failed deployments can be rolled back by redeploying the previous version
- **Logging and Monitoring**: Application logs and metrics are captured in CloudWatch
- **Security**: Secrets are stored in AWS Secrets Manager and accessed securely

## Setting Up the Pipeline

To set up the CI/CD pipeline:

1. Add the following secrets to your GitHub repository:
   - `AWS_ACCESS_KEY_ID`: AWS access key with appropriate permissions
   - `AWS_SECRET_ACCESS_KEY`: AWS secret access key
   - `DB_PASSWORD`: Database password for each environment

2. Bootstrap the initial infrastructure:
   ```bash
   ./deploy/terraform/bootstrap.sh