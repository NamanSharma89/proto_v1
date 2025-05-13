# deploy/terraform/outputs.tf

output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.networking.vpc_id
}

output "public_subnet_ids" {
  description = "The IDs of the public subnets"
  value       = module.networking.public_subnet_ids
}

output "private_subnet_ids" {
  description = "The IDs of the private subnets"
  value       = module.networking.private_subnet_ids
}

output "app_security_group_id" {
  description = "The ID of the application security group"
  value       = module.networking.app_security_group_id
}

output "db_security_group_id" {
  description = "The ID of the database security group"
  value       = module.networking.db_security_group_id
}

output "db_endpoint" {
  description = "The connection endpoint for the RDS database"
  value       = module.database.db_endpoint
}

output "db_name" {
  description = "The name of the RDS database"
  value       = module.database.db_name
}

output "ecr_repository_url" {
  description = "The URL of the ECR repository"
  value       = module.storage.ecr_repository_url
}

output "s3_bucket_name" {
  description = "The name of the S3 bucket"
  value       = module.storage.app_bucket_name
}

output "app_url" {
  description = "The URL of the deployed application"
  value       = "https://${module.app_deployment.alb_dns_name}"
}

output "notebook_url" {
  description = "The URL of the SageMaker notebook instance (dev environment only)"
  value       = var.enable_ml && var.environment == "dev-cloud" ? module.sagemaker[0].notebook_url : null
}

output "sns_topic_arn" {
  description = "The ARN of the SNS topic for notifications"
  value       = module.monitoring.sns_topic_arn
}