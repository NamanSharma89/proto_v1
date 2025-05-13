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

output "db_host_parameter_name" {
  description = "The name of the SSM Parameter Store parameter containing the database host"
  value       = aws_ssm_parameter.db_host.name
}

output "db_port_parameter_name" {
  description = "The name of the SSM Parameter Store parameter containing the database port"
  value       = aws_ssm_parameter.db_port.name
}

output "db_name_parameter_name" {
  description = "The name of the SSM Parameter Store parameter containing the database name"
  value       = aws_ssm_parameter.db_name.name
}

output "db_username_parameter_name" {
  description = "The name of the SSM Parameter Store parameter containing the database username"
  value       = aws_ssm_parameter.db_username.name
}

output "db_password_parameter_name" {
  description = "The name of the SSM Parameter Store parameter containing the database password"
  value       = var.db_password_parameter_name
}