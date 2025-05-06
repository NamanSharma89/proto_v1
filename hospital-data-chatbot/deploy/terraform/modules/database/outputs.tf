# deploy/terraform/modules/database/outputs.tf

output "db_endpoint" {
  description = "The connection endpoint for the RDS database"
  value       = aws_db_instance.postgres.endpoint
}

output "db_name" {
  description = "The name of the RDS database"
  value       = var.db_name
}

output "db_username" {
  description = "The master username for the RDS instance"
  value       = var.username
  sensitive   = true
}

output "db_credentials_arn" {
  description = "The ARN of the Secrets Manager secret containing the database credentials"
  value       = aws_secretsmanager_secret.db_credentials.arn
}