# deploy/terraform/modules/bedrock/variables.tf

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev-cloud, stage, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region to deploy to"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket for Bedrock to access"
  type        = string
}

variable "bedrock_model_id" {
  description = "ID of the Bedrock model to use"
  type        = string
  default     = "anthropic.claude-3-sonnet-20240229-v1:0"
}

variable "enable_streaming" {
  description = "Whether to enable streaming responses from Bedrock"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "bedrock_model_units" {
  description = "Number of model units to provision for Bedrock"
  type        = number
  default     = 1
}

variable "provision_dedicated_throughput" {
  description = "Whether to provision dedicated throughput for the Bedrock model"
  type        = bool
  default     = false
}