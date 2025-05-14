# modules/ml_api/variables.tf

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev-cloud, stage, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC where application will be deployed"
  type        = string
}

variable "public_subnet_ids" {
  description = "IDs of public subnets for the application load balancer"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "IDs of private subnets for the application containers"
  type        = list(string)
}

variable "app_security_group_id" {
  description = "ID of the security group for the application"
  type        = string
}

variable "ecr_repository_url" {
  description = "URL of the ECR repository containing the application image"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for application data"
  type        = string
}

variable "image_tag" {
  description = "Tag of the Docker image to deploy"
  type        = string
  default     = "latest"
}

variable "task_cpu" {
  description = "CPU units for the ECS task (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "task_memory" {
  description = "Memory for the ECS task in MB"
  type        = number
  default     = 2048
}

variable "desired_count" {
  description = "Desired count of tasks in the ECS service"
  type        = number
  default     = 1
}

variable "min_capacity" {
  description = "Minimum capacity for Auto Scaling"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum capacity for Auto Scaling"
  type        = number
  default     = 5
}

variable "logs_retention_days" {
  description = "Retention period for CloudWatch logs in days"
  type        = number
  default     = 30
}

variable "sns_topic_arn" {
  description = "ARN of the SNS topic for alarms"
  type        = string
}

variable "sagemaker_role_arn" {
  description = "ARN of the SageMaker execution role"
  type        = string
}

variable "db_host_parameter_name" {
  description = "Name of the SSM Parameter Store parameter containing the database host"
  type        = string
}

variable "db_port_parameter_name" {
  description = "Name of the SSM Parameter Store parameter containing the database port"
  type        = string
}

variable "db_name_parameter_name" {
  description = "Name of the SSM Parameter Store parameter containing the database name"
  type        = string
}

variable "db_username_parameter_name" {
  description = "Name of the SSM Parameter Store parameter containing the database username"
  type        = string
}

variable "db_password_parameter_name" {
  description = "Name of the SSM Parameter Store parameter containing the database password"
  type        = string
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}