# deploy/terraform/modules/app_deployment/outputs.tf

output "alb_dns_name" {
  description = "The DNS name of the application load balancer"
  value       = aws_lb.app.dns_name
}

output "alb_arn" {
  description = "The ARN of the application load balancer"
  value       = aws_lb.app.arn
}

output "ecs_cluster_name" {
  description = "The name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "The name of the ECS service"
  value       = aws_ecs_service.app.name
}

output "target_group_arn" {
  description = "The ARN of the target group"
  value       = aws_lb_target_group.app.arn
}

output "task_definition_arn" {
  description = "The ARN of the task definition"
  value       = aws_ecs_task_definition.app.arn
}