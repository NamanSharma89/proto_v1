# Terraform and provider versions configuration

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment to use remote state storage with S3 and DynamoDB
  # backend "s3" {
  #   # These values will be provided separately for each environment
  # }
}