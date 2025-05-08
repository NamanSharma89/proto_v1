# deploy/terraform/modules/app_deployment/locals.tf

locals {
  # Determine whether to use HTTPS based on certificate ARN
  use_https = var.acm_certificate_arn != ""
  
  # Helper to get the appropriate service name/id based on HTTPS configuration
  app_service_name = local.use_https ? aws_ecs_service.app_https[0].name : aws_ecs_service.app_http[0].name
  app_service_id   = local.use_https ? aws_ecs_service.app_https[0].id : aws_ecs_service.app_http[0].id
}