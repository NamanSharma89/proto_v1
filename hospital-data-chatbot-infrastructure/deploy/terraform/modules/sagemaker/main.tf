# deploy/terraform/modules/sagemaker/main.tf

resource "aws_iam_role" "sagemaker_role" {
  name = "${var.project_name}-${var.environment}-sagemaker-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-sagemaker-role"
  }
}

resource "aws_iam_policy" "sagemaker_policy" {
  name        = "${var.project_name}-${var.environment}-sagemaker-policy"
  description = "Policy for SageMaker access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:CreateBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket}",
          "arn:aws:s3:::${var.s3_bucket}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:DescribeVpcs",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "sagemaker_policy_attachment" {
  role       = aws_iam_role.sagemaker_role.name
  policy_arn = aws_iam_policy.sagemaker_policy.arn
}

# Create SageMaker Notebook Instance for development
resource "aws_sagemaker_notebook_instance" "dev_notebook" {
  count = var.environment == "dev-cloud" ? 1 : 0

  name                    = "${var.project_name}-${var.environment}-notebook"
  role_arn                = aws_iam_role.sagemaker_role.arn
  instance_type           = "ml.t3.medium"
  subnet_id               = var.subnet_ids[0]
  security_groups         = [var.security_group_id]
  lifecycle_config_name   = aws_sagemaker_notebook_instance_lifecycle_configuration.notebook_config[0].name
  direct_internet_access  = "Enabled"
  
  tags = {
    Name = "${var.project_name}-${var.environment}-notebook"
  }
}

resource "aws_sagemaker_notebook_instance_lifecycle_configuration" "notebook_config" {
  count = var.environment == "dev-cloud" ? 1 : 0
  
  name = "${var.project_name}-${var.environment}-notebook-config"
  
  on_start = base64encode(<<-EOF
    #!/bin/bash
    set -e
    
    # Install necessary packages
    sudo -u ec2-user -i <<'EOF2'
    pip install polars pandas scikit-learn fastapi uvicorn
    pip install boto3 botocore psycopg2-binary
    
    # Clone the repository (if using Git)
    # git clone https://github.com/your-org/${var.project_name}.git
    EOF2
  EOF
  )
}

# Create a SageMaker Model Registry
resource "aws_sagemaker_model_package_group" "hospital_models" {
  model_package_group_name = "${var.project_name}-${var.environment}-models"
  
  tags = {
    Name = "${var.project_name}-${var.environment}-model-registry"
  }
}

# Output the SageMaker role ARN for use in other modules
output "sagemaker_role_arn" {
  value = aws_iam_role.sagemaker_role.arn
}

output "notebook_url" {
  value = var.environment == "dev-cloud" ? aws_sagemaker_notebook_instance.dev_notebook[0].url : null
}