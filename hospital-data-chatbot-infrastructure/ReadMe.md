# AWS Infrastructure Management with Terraform

![Terraform Logo](https://www.terraform.io/assets/images/logo-hashicorp-3f10732f.svg)

## 🚀 Overview

This repository contains a comprehensive AWS infrastructure management system powered by Terraform. It provides a streamlined approach to deploying and managing multi-environment AWS infrastructure (development, staging, and production) using infrastructure as code.

## ✨ Features

- **Multi-environment Support**: Maintain separate configurations for development, staging, and production
- **Infrastructure as Code**: Define all your infrastructure components in version-controlled code
- **Automated Deployment**: Deploy your entire infrastructure stack with a single command
- **Environment Isolation**: Keep resources separated by environment to prevent cross-contamination
- **Consistent Configuration**: Ensure infrastructure consistency across all environments
- **Complete AWS Stack**: Includes VPC, subnets, security groups, EC2 instances, S3 buckets, and monitoring
- **Scalable Architecture**: Easily extend with additional AWS resources as needed
- **AI/ML Integration**: Built-in support for AWS Bedrock and SageMaker

## 📂 Repository Structure

```
terraform/
├── main.tf                # Primary infrastructure definition
├── variables.tf           # Variable declarations
├── outputs.tf             # Output definitions
├── versions.tf            # Terraform version constraints
├── environments/
│   ├── dev.tfvars         # Development environment configuration
│   ├── staging.tfvars     # Staging environment configuration
│   ├── prod.tfvars        # Production environment configuration
│   └── backend-config/
│       ├── dev.hcl        # Remote state config for development
│       ├── staging.hcl    # Remote state config for staging
│       └── prod.hcl       # Remote state config for production
├── modules/               # Reusable Terraform modules
│   ├── networking/        # VPC, subnets, security groups
│   ├── database/          # RDS PostgreSQL configuration
│   ├── storage/           # S3 buckets, ECR repositories
│   ├── app_deployment/    # ECS Fargate, ALB, auto-scaling
│   ├── monitoring/        # CloudWatch, SNS
│   ├── bedrock/           # AI model integration
│   └── sagemaker/         # ML infrastructure
├── bootstrap.sh           # Script to initialize backend infrastructure
└── terraform-infra-manager.sh  # Management script
```

## 🛠️ Prerequisites

- **AWS CLI**: Configured with appropriate credentials
- **Terraform**: Version 1.0.0 or later
- **Bash**: For running the management script
- **AWS Account**: With permissions to create all required resources
- **AWS IAM User**: With programmatic access and appropriate permissions

## 🏁 Getting Started

1. **Clone this repository**

```bash
git clone https://github.com/your-org/aws-terraform-infra.git
cd aws-terraform-infra
```

2. **Make the management scripts executable**

```bash
chmod +x terraform-infra-manager.sh bootstrap.sh
```

3. **Set up AWS credentials**

Choose one of the following methods to configure AWS credentials:

#### Method 1: AWS CLI Configuration (Recommended)
```bash
aws configure
```
Enter your AWS Access Key, Secret Key, default region, and output format when prompted.

#### Method 2: Environment Variables
```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="ap-south-1"
```

#### Method 3: Configuration File for the Script
Create a `.awsconfig` file in your project root:
```bash
# AWS credentials configuration
AWS_ACCESS_KEY_ID=your-access-key-here
AWS_SECRET_ACCESS_KEY=your-secret-key-here
AWS_DEFAULT_REGION=ap-south-1
```

Add to your `.gitignore`:
```
.awsconfig
```

4. **Bootstrap your Terraform state infrastructure**

```bash
./bootstrap.sh --environment dev-cloud --region ap-south-1 --profile your-aws-profile
```

This sets up the required S3 bucket and DynamoDB table for Terraform state management.

5. **Update configuration files**

Modify the `.tfvars` files in the `environments` directory to match your requirements:
- Update AWS region and account ID
- Configure networking (CIDR blocks, subnets)
- Set appropriate security group rules
- Adjust instance types and counts for each environment

6. **Set up sensitive variables**

```bash
# Edit terraform-secrets.sh with appropriate values
vim terraform-secrets.sh

# Make it executable
chmod +x terraform-secrets.sh

# Source it before running terraform commands
source ./terraform-secrets.sh
```

7. **Initialize Terraform**

```bash
./terraform-infra-manager.sh init
```

8. **Deploy to your desired environment**

```bash
./terraform-infra-manager.sh -e dev-cloud apply
```

## 🌟 terraform-infra-manager.sh

The `terraform-infra-manager.sh` script is a powerful utility for managing your Terraform infrastructure. It provides a streamlined workflow for initializing, planning, applying, and destroying infrastructure across different environments.

### Key Features

- **Environment Management**: Easily switch between development, staging, and production environments
- **AWS Profile Handling**: Use different AWS credentials for different environments
- **S3 Backend Verification**: Automatically checks for and offers to create required S3 buckets
- **DynamoDB State Locking**: Ensures safe concurrent access to Terraform state
- **Performance Timing**: Tracks and reports the duration of Terraform operations
- **Verbose Mode**: Provides detailed output for troubleshooting
- **Backend Configuration**: Automatically manages backend configurations for different environments
- **Auto-approve Option**: Supports non-interactive deployment for CI/CD pipelines
- **Full Command Support**: Supports all Terraform commands including initialization, plan, apply, destroy, and more

### Script Usage

```bash
Usage: ./terraform-infra-manager.sh [OPTIONS] COMMAND

A utility script to manage Terraform infrastructure

Commands:
  init        Initialize Terraform working directory
  plan        Generate and show an execution plan
  apply       Build or change infrastructure
  destroy     Destroy previously-created infrastructure
  output      Show output values from your root module
  validate    Check whether the configuration is valid
  workspace   Switch between workspaces
  fmt         Reformat your configuration in the standard style
  all         Run init, validate, plan, and apply in sequence

Options:
  -d, --directory DIR   Terraform directory (default: ./terraform)
  -e, --environment ENV Environment to deploy (dev-cloud, staging, prod)
  -a, --auto-approve    Skip interactive approval for apply/destroy
  -v, --verbose         Show detailed output
  -h, --help            Display this help message
  --profile PROFILE     AWS profile to use (default: Your configured profile)
```

### Advanced Features

#### S3 Bucket and DynamoDB Table Management

The script automatically checks if the required S3 bucket and DynamoDB table for Terraform state management exist:

```bash
# S3 bucket check
BUCKET_NAME="${PROJECT_NAME}-terraform-state-${BUCKET_ENV}-${AWS_ACCOUNT_ID}"
if check_s3_bucket_exists "$BUCKET_NAME" "$AWS_REGION"; then
    echo "✅ S3 bucket '$BUCKET_NAME' exists and is accessible"
else
    echo "⚠️ S3 bucket '$BUCKET_NAME' does not exist or is not accessible"
    read -p "Do you want to create the S3 bucket? (y/n): " CREATE_BUCKET
    # ... bucket creation logic ...
fi

# DynamoDB table check
DYNAMO_TABLE="${PROJECT_NAME}-terraform-locks-${BUCKET_ENV}"
if aws dynamodb describe-table --table-name "$DYNAMO_TABLE" --region "$AWS_REGION" &>/dev/null; then
    echo "✅ DynamoDB table '$DYNAMO_TABLE' exists and is accessible"
else
    echo "⚠️ DynamoDB table '$DYNAMO_TABLE' does not exist or is not accessible"
    # ... table creation logic ...
fi
```

#### Backend Configuration Generation

The script automatically generates the correct backend configuration for each environment:

```bash
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
    # ... simplified config ...
fi
```

#### Performance Tracking

The script includes built-in timing functionality to track the duration of Terraform operations:

```bash
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

# Usage within the script
start_time=$(timer)
terraform $cmd $args
timer $start_time
```

#### Full Deployment Pipeline

The script supports a complete deployment pipeline with a single command:

```bash
./terraform-infra-manager.sh -e dev-cloud all
```

This runs `init`, `validate`, `plan`, and `apply` in sequence, providing a complete deployment workflow.

## 🔄 Deployment Workflow

1. **Development First**: Deploy changes to the development environment
   ```bash
   ./terraform-infra-manager.sh -e dev-cloud apply
   ```

2. **Validate in Staging**: Once tested in development, promote to staging
   ```bash
   ./terraform-infra-manager.sh -e staging apply
   ```

3. **Production Deployment**: After thorough testing, deploy to production
   ```bash
   ./terraform-infra-manager.sh -e prod apply
   ```

## 🔐 State Management

This infrastructure uses remote state management to enable team collaboration:

```bash
# Initialize with remote state for development
./terraform-infra-manager.sh -e dev-cloud init

# Initialize with remote state for staging
./terraform-infra-manager.sh -e staging init

# Initialize with remote state for production
./terraform-infra-manager.sh -e prod init
```

## 📊 Infrastructure Visualization

To generate a visual representation of your infrastructure:

```bash
terraform graph | dot -Tpng > infrastructure.png
```

## ⚙️ Customization

### Adding New Resources

1. Add resource definitions to `main.tf`
2. Declare any new variables in `variables.tf`
3. Update environment configuration in `.tfvars` files
4. Add outputs if needed in `outputs.tf`

### Creating a New Environment

1. Create a new `.tfvars` file in the `environments` directory
2. Create a new backend configuration file if using remote state
3. Deploy using the new environment name:
   ```bash
   ./terraform-infra-manager.sh -e new-environment apply
   ```

## 🚨 Best Practices

- **Version Control**: Always commit changes to your Terraform files
- **Code Review**: Use pull requests to review infrastructure changes
- **Testing**: Test changes in lower environments before promoting
- **Linting**: Use `terraform fmt` to maintain consistent formatting
- **Documentation**: Update comments and README as infrastructure evolves
- **State Backup**: Regularly backup your Terraform state
- **Secret Management**: Avoid storing secrets in Terraform files

## 🔐 AWS Credential Management

The infrastructure manager script supports several methods for handling AWS credentials. Choose the approach that best fits your security requirements and workflow.

### Available Credential Methods

#### 1. AWS CLI Profiles (Recommended)

Use AWS profiles for the most secure approach:

```bash
# Configure a named profile
aws configure --profile terraform-admin

# Use the profile with the script
./terraform-infra-manager.sh --profile terraform-admin -e dev-cloud apply
```

#### 2. Environment Variables

Set credentials for the current session:

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="ap-south-1"

# Then run the script normally
./terraform-infra-manager.sh -e dev-cloud apply
```

#### 3. Configuration File

Create a `.awsconfig` file with your credentials:

```
AWS_ACCESS_KEY_ID=your-access-key-here
AWS_SECRET_ACCESS_KEY=your-secret-key-here
AWS_DEFAULT_REGION=ap-south-1
```

The script will automatically load this file if present.

#### 4. AWS IAM Roles (For EC2 Instances)

If running on EC2, use IAM roles for best security:

```bash
# No credentials needed, AWS SDK will use the instance profile
./terraform-infra-manager.sh -e prod apply
```

### Security Best Practices

- **Never commit credentials** to version control
- **Rotate keys** regularly
- **Use temporary credentials** when possible
- **Apply least privilege principle** to IAM permissions
- **Enable MFA** for AWS accounts with infrastructure access
- **Audit credential usage** regularly

## 🔍 Troubleshooting

### Common Issues

- **State Lock**: If a state lock persists, check for running operations or use:
  ```bash
  terraform force-unlock LOCK_ID
  ```

- **Provider Authentication**: Ensure AWS credentials are properly configured:
  ```bash
  aws configure list
  ```

- **Resource Limits**: Check for AWS service quotas if deployments fail

- **Credential Issues**: Verify your credentials are working:
  ```bash
  aws sts get-caller-identity
  ```

- **Permission Issues**: Ensure your AWS identity has the necessary permissions:
  ```bash
  # Example error
  Error: creating ECS Cluster: AccessDeniedException: User is not authorized to perform: ecs:CreateCluster
  ```
  
  Solution: Add the required permissions to your IAM user/role or use a role with appropriate permissions.

### Debugging

Enable verbose logging for more detailed output:

```bash
./terraform-infra-manager.sh -v -e dev-cloud plan
```

### Required AWS Permissions

To run the infrastructure deployment, your AWS identity needs the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "rds:*",
        "s3:*",
        "ecr:*",
        "ecs:*",
        "elasticloadbalancing:*",
        "application-autoscaling:*",
        "cloudwatch:*",
        "logs:*",
        "sns:*",
        "secretsmanager:*",
        "sagemaker:*",
        "bedrock:*",
        "dynamodb:*",
        "route53:*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:GetRole",
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:PutRolePolicy",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:CreatePolicy",
        "iam:DeletePolicy",
        "iam:TagRole",
        "iam:ListRoleTags"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": [
        "arn:aws:iam::ACCOUNT_ID:role/PROJECT_NAME-*-ecs-execution-role",
        "arn:aws:iam::ACCOUNT_ID:role/PROJECT_NAME-*-ecs-task-role",
        "arn:aws:iam::ACCOUNT_ID:role/PROJECT_NAME-*-bedrock-role",
        "arn:aws:iam::ACCOUNT_ID:role/PROJECT_NAME-*-sagemaker-role"
      ],
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": [
            "ecs.amazonaws.com",
            "ecs-tasks.amazonaws.com",
            "bedrock.amazonaws.com",
            "sagemaker.amazonaws.com",
            "lambda.amazonaws.com",
            "monitoring.rds.amazonaws.com"
          ]
        }
      }
    }
  ]
}
```

Replace `ACCOUNT_ID` with your AWS account ID and `PROJECT_NAME` with your project name.

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `terraform fmt` and `terraform validate`
5. Submit a pull request

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- HashiCorp for creating Terraform
- AWS for their comprehensive cloud infrastructure
- The community for sharing best practices and modules

---

Built with ❤️ by Your Team