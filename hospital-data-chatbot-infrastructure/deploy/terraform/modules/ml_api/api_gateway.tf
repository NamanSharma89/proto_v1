# modules/ml_api/api_gateway.tf

resource "aws_api_gateway_rest_api" "ml_api" {
  name        = "${var.project_name}-${var.environment}-ml-api"
  description = "API Gateway for ML API"
  
  endpoint_configuration {
    types = ["REGIONAL"]
  }
  
  tags = var.tags
}

resource "aws_api_gateway_resource" "ml_api_proxy" {
  rest_api_id = aws_api_gateway_rest_api.ml_api.id
  parent_id   = aws_api_gateway_rest_api.ml_api.root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "ml_api_proxy" {
  rest_api_id   = aws_api_gateway_rest_api.ml_api.id
  resource_id   = aws_api_gateway_resource.ml_api_proxy.id
  http_method   = "ANY"
  authorization = "NONE"
  api_key_required = true  # Require API key for security
  
  request_parameters = {
    "method.request.path.proxy" = true
  }
}

resource "aws_api_gateway_integration" "ml_api_proxy" {
  rest_api_id = aws_api_gateway_rest_api.ml_api.id
  resource_id = aws_api_gateway_resource.ml_api_proxy.id
  http_method = aws_api_gateway_method.ml_api_proxy.http_method
  
  type                    = "HTTP_PROXY"
  integration_http_method = "ANY"
  # Use the actual ALB DNS name defined in main.tf
  uri                     = "http://${aws_lb.ml_api.dns_name}/{proxy}"
  
  connection_type      = "VPC_LINK"
  connection_id        = aws_api_gateway_vpc_link.ml_api.id
  
  request_parameters = {
    "integration.request.path.proxy" = "method.request.path.proxy"
  }
}

resource "aws_api_gateway_method" "ml_api_root" {
  rest_api_id   = aws_api_gateway_rest_api.ml_api.id
  resource_id   = aws_api_gateway_rest_api.ml_api.root_resource_id
  http_method   = "ANY"
  authorization = "NONE"
  api_key_required = true  # Require API key for security
}

resource "aws_api_gateway_integration" "ml_api_root" {
  rest_api_id = aws_api_gateway_rest_api.ml_api.id
  resource_id = aws_api_gateway_rest_api.ml_api.root_resource_id
  http_method = aws_api_gateway_method.ml_api_root.http_method
  
  type                    = "HTTP_PROXY" 
  integration_http_method = "ANY"
  # Use the actual ALB DNS name defined in main.tf
  uri                     = "http://${aws_lb.ml_api.dns_name}/"
  
  connection_type      = "VPC_LINK"
  connection_id        = aws_api_gateway_vpc_link.ml_api.id
}

# Create a VPC Link for the API Gateway to connect to the internal ALB
resource "aws_api_gateway_vpc_link" "ml_api" {
  name        = "${var.project_name}-${var.environment}-ml-api-vpc-link"
  description = "VPC Link for ML API ALB"
  target_arns = [aws_lb.ml_api.arn]
}

resource "aws_api_gateway_deployment" "ml_api" {
  depends_on = [
    aws_api_gateway_integration.ml_api_proxy,
    aws_api_gateway_integration.ml_api_root
  ]
  
  rest_api_id = aws_api_gateway_rest_api.ml_api.id
  stage_name  = var.environment
  
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_api_key" "ml_api" {
  name = "${var.project_name}-${var.environment}-ml-api-key"
}

resource "aws_api_gateway_usage_plan" "ml_api" {
  name = "${var.project_name}-${var.environment}-ml-api-usage-plan"
  
  api_stages {
    api_id = aws_api_gateway_rest_api.ml_api.id
    stage  = aws_api_gateway_deployment.ml_api.stage_name
  }
  
  quota_settings {
    limit  = 10000
    period = "MONTH"
  }
  
  throttle_settings {
    burst_limit = 100
    rate_limit  = 50
  }
}

resource "aws_api_gateway_usage_plan_key" "ml_api" {
  key_id        = aws_api_gateway_api_key.ml_api.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.ml_api.id
}

# CloudWatch alarms for API Gateway
resource "aws_cloudwatch_metric_alarm" "api_gateway_5xx" {
  alarm_name          = "${var.project_name}-${var.environment}-ml-api-gateway-5xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = "60"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This alarm monitors for 5XX errors in the ML API Gateway"
  alarm_actions       = [var.sns_topic_arn]
  
  dimensions = {
    ApiName = aws_api_gateway_rest_api.ml_api.name
    Stage   = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_4xx" {
  alarm_name          = "${var.project_name}-${var.environment}-ml-api-gateway-4xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = "60"
  statistic           = "Sum"
  threshold           = "20"
  alarm_description   = "This alarm monitors for excessive 4XX errors in the ML API Gateway"
  alarm_actions       = [var.sns_topic_arn]
  
  dimensions = {
    ApiName = aws_api_gateway_rest_api.ml_api.name
    Stage   = var.environment
  }
}