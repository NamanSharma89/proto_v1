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

2. **Make the management script executable**

```bash
chmod +x terraform-infra-manager.sh
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
export AWS_DEFAULT_REGION="us-east-1"
```

#### Method 3: Configuration File for the Script
Create a `.awsconfig` file in your project root:
```bash
# AWS credentials configuration
AWS_ACCESS_KEY_ID=your-access-key-here
AWS_SECRET_ACCESS_KEY=your-secret-key-here
AWS_DEFAULT_REGION=us-east-1
```

Add to your `.gitignore`:
```
.awsconfig
```

4. **Update configuration files**

Modify the `.tfvars` files in the `environments` directory to match your requirements:
- Update AWS region and account ID
- Configure networking (CIDR blocks, subnets)
- Set appropriate security group rules
- Adjust instance types and counts for each environment

5. **Initialize Terraform**

```bash
./terraform-infra-manager.sh init
```

6. **Deploy to your desired environment**

```bash
./terraform-infra-manager.sh -e dev apply
```

## 🌟 Usage Examples

### Initialize Terraform

```bash
./terraform-infra-manager.sh init
```

### View Execution Plan

```bash
./terraform-infra-manager.sh -e staging plan
```

### Deploy Infrastructure

```bash
./terraform-infra-manager.sh -e prod apply
```

### Auto-Approve Changes

```bash
./terraform-infra-manager.sh -e dev -a apply
```

### Destroy Infrastructure

```bash
./terraform-infra-manager.sh -e dev destroy
```

### Run Full Deployment Pipeline

```bash
./terraform-infra-manager.sh -e staging -a all
```

### View Infrastructure Outputs

```bash
./terraform-infra-manager.sh -e prod output
```

### Format Terraform Files

```bash
./terraform-infra-manager.sh fmt
```

### Switch Workspace

```bash
./terraform-infra-manager.sh workspace
```

## 🔄 Deployment Workflow

1. **Development First**: Deploy changes to the development environment
   ```bash
   ./terraform-infra-manager.sh -e dev apply
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
terraform init -backend-config=environments/backend-config/dev.hcl

# Initialize with remote state for staging
terraform init -backend-config=environments/backend-config/staging.hcl

# Initialize with remote state for production
terraform init -backend-config=environments/backend-config/prod.hcl
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
./terraform-infra-manager.sh --profile terraform-admin -e dev apply
```

#### 2. Environment Variables

Set credentials for the current session:

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"

# Then run the script normally
./terraform-infra-manager.sh -e dev apply
```

#### 3. Configuration File

Create a `.awsconfig` file with your credentials:

```
AWS_ACCESS_KEY_ID=your-access-key-here
AWS_SECRET_ACCESS_KEY=your-secret-key-here
AWS_DEFAULT_REGION=us-east-1
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

### Debugging

Enable verbose logging for more detailed output:

```bash
./terraform-infra-manager.sh -v -e dev plan
```

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