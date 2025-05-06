# deploy/terraform/modules/monitoring/main.tf

# Create SNS topic for alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-${var.environment}-alerts"
  
  tags = merge(
    {
      Name = "${var.project_name}-${var.environment}-alerts"
    },
    var.tags
  )
}

# Create SNS subscription for email alerts
resource "aws_sns_topic_subscription" "email_subscription" {
  count     = var.alarm_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# CloudWatch Log Group for application logs
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/app/${var.project_name}/${var.environment}"
  retention_in_days = var.logs_retention_days
  
  tags = merge(
    {
      Name = "${var.project_name}-${var.environment}-logs"
    },
    var.tags
  )
}

# CloudWatch Dashboard for application metrics
resource "aws_cloudwatch_dashboard" "main_dashboard" {
  dashboard_name = "${var.project_name}-${var.environment}-dashboard"
  
  # Simple dashboard with CPU and memory metrics
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", "${var.project_name}-${var.environment}-service", "ClusterName", "${var.project_name}-${var.environment}", { "stat": "Average" }]
          ]
          view    = "timeSeries"
          stacked = false
          title   = "CPU Utilization"
          region  = data.aws_region.current.name
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ECS", "MemoryUtilization", "ServiceName", "${var.project_name}-${var.environment}-service", "ClusterName", "${var.project_name}-${var.environment}", { "stat": "Average" }]
          ]
          view    = "timeSeries"
          stacked = false
          title   = "Memory Utilization"
          region  = data.aws_region.current.name
          period  = 300
        }
      }
    ]
  })
}

# Get current AWS region
data "aws_region" "current" {}

# CloudWatch Alarm for application errors
resource "aws_cloudwatch_metric_alarm" "app_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-app-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "HTTPCode_ELB_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "This alarm monitors for excessive 5XX errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    LoadBalancer = "app/${var.project_name}-${var.environment}-alb/*"
  }
  
  tags = merge(
    {
      Name = "${var.project_name}-${var.environment}-app-errors-alarm"
    },
    var.tags
  )
}