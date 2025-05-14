# modules/ml_api/outputs.tf

output "ml_api_url" {
  description = "URL of the ML API Gateway endpoint"
  value       = "${aws_api_gateway_deployment.ml_api.invoke_url}"
}

output "ml_api_key" {
  description = "API key for the ML API"
  value       = aws_api_gateway_api_key.ml_api.value
  sensitive   = true
}

output "ml_api_alb_dns_name" {
  description = "DNS name of the ML API load balancer"
  value       = aws_lb.ml_api.dns_name
}

output "ml_api_cluster_name" {
  description = "Name of the ML API ECS cluster"
  value       = aws_ecs_cluster.ml_api.name
}

output "ml_api_service_name" {
  description = "Name of the ML API ECS service"
  value       = aws_ecs_service.ml_api.name
}

output "ml_api_task_definition_arn" {
  description = "ARN of the ML API task definition"
  value       = aws_ecs_task_definition.ml_api.arn
}

output "ml_api_execution_role_arn" {
  description = "ARN of the ML API execution role"
  value       = aws_iam_role.ml_api_execution.arn
}

output "ml_api_task_role_arn" {
  description = "ARN of the ML API task role"
  value       = aws_iam_role.ml_api_task.arn
}