# deploy/terraform/main.tf

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.97.0"
    }
  }

  backend "s3" {
    # Backend configuration will be provided via backend-config files
  }
}

# Common tags for all resources
locals {
  common_tags = merge(
    {
      Environment = var.environment
      Project     = var.project_name
      ManagedBy   = "Terraform"
    },
    var.additional_tags
  )
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = local.common_tags
  }
}

# Monitoring module - CloudWatch dashboards, alarms, SNS topics
module "monitoring" {
  source = "./modules/monitoring"

  project_name        = var.project_name
  environment         = var.environment
  alarm_email         = var.alarm_email
  logs_retention_days = var.logs_retention_days
  
  tags = local.common_tags
}

# Networking module - VPC, subnets, security groups
module "networking" {
  source = "./modules/networking"

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  enable_nat_gateway = var.enable_nat_gateway
  
  # Pass common tags to the module - this will only work if tags variable is defined in networking module
  tags = local.common_tags
}

# Storage module - S3 buckets, ECR repository
module "storage" {
  source = "./modules/storage"

  project_name = var.project_name
  environment  = var.environment
  
  tags = local.common_tags
}

# Database module - RDS PostgreSQL
module "database" {
  source = "./modules/database"

  project_name      = var.project_name
  environment       = var.environment
  vpc_id            = module.networking.vpc_id
  subnet_ids        = module.networking.private_subnet_ids
  security_group_id = module.networking.db_security_group_id
  
  instance_class    = var.db_instance_class
  allocated_storage = var.db_allocated_storage
  db_name           = "hospital_data_${replace(var.environment, "-", "_")}"
  username = "${replace(var.environment, "-", "_")}_user"
  password          = var.db_password
  
  # Pass common tags to the module - this will only work if tags variable is defined in database module
  tags = local.common_tags
}

# Bedrock module - IAM roles and policies for Bedrock access
module "bedrock" {
  source = "./modules/bedrock"

  project_name     = var.project_name
  environment      = var.environment
  aws_region       = var.aws_region
  s3_bucket_arn    = module.storage.app_bucket_arn
  bedrock_model_id = var.bedrock_model_id
  enable_streaming = true  # Fixed: direct value instead of variable reference
  
  tags = local.common_tags
}

# SageMaker module - ML infrastructure
module "sagemaker" {
  count  = var.enable_ml ? 1 : 0
  source = "./modules/sagemaker"

  project_name            = var.project_name
  environment             = var.environment
  s3_bucket               = module.storage.app_bucket_name
  vpc_id                  = module.networking.vpc_id
  subnet_ids              = module.networking.private_subnet_ids
  security_group_id       = module.networking.app_security_group_id
  
  instance_type           = var.notebook_instance_type
  deploy_notebook         = var.environment == "dev-cloud"
  training_instance_type  = var.training_instance_type
  inference_instance_type = var.inference_instance_type
  
  tags = local.common_tags
}

# App deployment module - ECS Fargate, ALB, auto-scaling
module "app_deployment" {
  source = "./modules/app_deployment"

  project_name          = var.project_name
  environment           = var.environment
  aws_region            = var.aws_region
  
  vpc_id                = module.networking.vpc_id
  public_subnet_ids     = module.networking.public_subnet_ids
  private_subnet_ids    = module.networking.private_subnet_ids
  app_security_group_id = module.networking.app_security_group_id
  
  ecr_repository_url    = module.storage.ecr_repository_url
  s3_bucket_name        = module.storage.app_bucket_name
  db_credentials_arn    = module.database.db_credentials_arn
  
  image_tag             = var.image_tag
  acm_certificate_arn   = var.acm_certificate_arn
  
  task_cpu              = var.task_cpu
  task_memory           = var.task_memory
  desired_count         = var.desired_count
  min_capacity          = var.min_capacity
  max_capacity          = var.max_capacity
  
  health_check_path     = "/api/health"
  container_port        = 8080
  host_port             = 8080
  
  domain_name           = var.domain_name
  create_route53_record = var.create_route53_record
  route53_zone_id       = var.route53_zone_id
  
  sns_topic_arn         = module.monitoring.sns_topic_arn
  logs_retention_days   = var.logs_retention_days
  
  environment_variables = {
    APP_ENV            = var.environment
    BEDROCK_MODEL_ID   = var.bedrock_model_id
    USE_S3             = "True"
    S3_BUCKET          = module.storage.app_bucket_name
    AWS_REGION         = var.aws_region
  }
  
  tags = local.common_tags
}