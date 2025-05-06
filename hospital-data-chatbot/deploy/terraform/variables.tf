# Variables for AWS infrastructure

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
}

variable "enable_nat_gateway" {
  description = "Whether to create a NAT Gateway"
  type        = bool
  default     = false
}

variable "web_ingress_cidr" {
  description = "CIDR blocks to allow HTTP/HTTPS traffic"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "ssh_ingress_cidr" {
  description = "CIDR blocks to allow SSH traffic"
  type        = list(string)
}

variable "s3_versioning_enabled" {
  description = "Enable versioning for S3 buckets"
  type        = bool
  default     = true
}

variable "web_instance_count" {
  description = "Number of web server instances"
  type        = number
  default     = 1
}

variable "web_instance_type" {
  description = "EC2 instance type for web servers"
  type        = string
}

variable "web_instance_volume_size" {
  description = "Size of the root volume for web servers in GB"
  type        = number
  default     = 20
}

variable "ec2_ami_id" {
  description = "AMI ID for EC2 instances"
  type        = string
}

variable "ssh_key_name" {
  description = "Name of the SSH key pair"
  type        = string
}

variable "cpu_alarm_threshold" {
  description = "Threshold for CPU utilization alarm"
  type        = number
  default     = 80
}

variable "enable_sns_alerts" {
  description = "Enable SNS notifications for alarms"
  type        = bool
  default     = false
}

variable "alert_email_addresses" {
  description = "Email addresses for alarm notifications"
  type        = list(string)
  default     = []
}