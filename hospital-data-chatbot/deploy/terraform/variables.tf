# deploy/terraform/variables.tf

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "hdc"
}

variable "environment" {
  description = "Deployment environment (dev-cloud, stage, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "ap-south-1"
}

# Network variables
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones to use"
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]
}

variable "enable_nat_gateway" {
  description = "Whether to provision a NAT Gateway for private subnets"
  type        = bool
  default     = false
}

# Database variables
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "Allocated storage for RDS instance (GB)"
  type        = number
  default     = 20
}

variable "db_password" {
  description = "Password for the database"
  type        = string
  sensitive   = true
}

# Application deployment variables
variable "task_cpu" {
  description = "CPU units for ECS task (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "task_memory" {
  description = "Memory for ECS task (MB)"
  type        = number
  default     = 2048
}

variable "desired_count" {
  description = "Desired count of ECS tasks"
  type        = number
  default     = 1
}

variable "min_capacity" {
  description = "Minimum number of ECS tasks"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of ECS tasks"
  type        = number
  default     = 5
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "acm_certificate_arn" {
  description = "ARN of ACM certificate for HTTPS"
  type        = string
  default     = ""
}

# Monitoring variables
variable "alarm_email" {
  description = "Email address for alarm notifications"
  type        = string
  default     = ""
}

# ML-related variables
variable "enable_ml" {
  description = "Whether to enable ML infrastructure"
  type        = bool
  default     = true
}

variable "bedrock_model_id" {
  description = "ID of the Bedrock model to use"
  type        = string
  default     = "anthropic.claude-3-sonnet-20240229-v1:0"
}

# Additional variables to add to deploy/terraform/variables.tf

# ML-related variables that were missing
variable "notebook_instance_type" {
  description = "Instance type for SageMaker notebook instances"
  type        = string
  default     = "ml.t3.medium"
}

variable "training_instance_type" {
  description = "Instance type for SageMaker training jobs"
  type        = string
  default     = "ml.m5.large"
}

variable "inference_instance_type" {
  description = "Instance type for SageMaker inference endpoints"
  type        = string
  default     = "ml.t2.medium"
}

# Domain-related variables
variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

variable "create_route53_record" {
  description = "Whether to create a Route 53 record for the domain"
  type        = bool
  default     = false
}

variable "route53_zone_id" {
  description = "ID of the Route 53 hosted zone"
  type        = string
  default     = ""
}

# Monitoring variables
variable "logs_retention_days" {
  description = "Retention period for CloudWatch logs in days"
  type        = number
  default     = 30
}

# Additional missing variables to add to your variables.tf

variable "enable_streaming" {
  description = "Whether to enable streaming responses from Bedrock"
  type        = bool
  default     = true
}

variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

