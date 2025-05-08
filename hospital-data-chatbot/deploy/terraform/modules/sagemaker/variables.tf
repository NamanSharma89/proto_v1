# deploy/terraform/modules/sagemaker/variables.tf

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev-cloud, stage, prod)"
  type        = string
}

variable "s3_bucket" {
  description = "Name of the S3 bucket for SageMaker data"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC where SageMaker resources will be deployed"
  type        = string
}

variable "subnet_ids" {
  description = "IDs of subnets where SageMaker resources will be deployed"
  type        = list(string)
}

variable "security_group_id" {
  description = "ID of the security group for SageMaker resources"
  type        = string
}

variable "instance_type" {
  description = "Instance type for SageMaker notebook instances"
  type        = string
  default     = "ml.t3.medium"
}

variable "volume_size" {
  description = "Volume size in GB for SageMaker notebook instances"
  type        = number
  default     = 20
}

variable "direct_internet_access" {
  description = "Whether to enable direct internet access for notebook instances"
  type        = bool
  default     = true
}

variable "deploy_notebook" {
  description = "Whether to deploy a SageMaker notebook instance"
  type        = bool
  default     = true
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

variable "inference_instance_count" {
  description = "Number of instances for SageMaker inference endpoints"
  type        = number
  default     = 1
}

variable "autoscaling_enabled" {
  description = "Whether to enable autoscaling for inference endpoints"
  type        = bool
  default     = false
}

variable "autoscaling_min_capacity" {
  description = "Minimum capacity for autoscaling"
  type        = number
  default     = 1
}

variable "autoscaling_max_capacity" {
  description = "Maximum capacity for autoscaling"
  type        = number
  default     = 5
}

variable "use_existing_role" {
  description = "Whether to use an existing IAM role for SageMaker"
  type        = bool
  default     = false
}

variable "existing_role_arn" {
  description = "ARN of an existing IAM role to use for SageMaker (if use_existing_role is true)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}