# deploy/terraform/modules/monitoring/outputs.tf

output "sns_topic_arn" {
  description = "The ARN of the SNS topic for notifications"
  value       = aws_sns_topic.alerts.arn
}

output "log_group_name" {
  description = "The name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.app_logs.name
}

output "dashboard_name" {
  description = "The name of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main_dashboard.dashboard_name
}