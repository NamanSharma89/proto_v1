# modules/ml_api/main.tf

data "aws_caller_identity" "current" {}

# Create an ECS Cluster for ML API
resource "aws_ecs_cluster" "ml_api" {
  name = "${var.project_name}-${var.environment}-ml-api-cluster"

  setting {
    name  = "containerInsights"
    value = var.environment == "prod" ? "enabled" : "disabled"
  }

  tags = var.tags
}

# Create IAM roles for ML API ECS tasks
resource "aws_iam_role" "ml_api_execution" {
  name = "${var.project_name}-${var.environment}-ml-api-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role" "ml_api_task" {
  name = "${var.project_name}-${var.environment}-ml-api-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# Attach policies to roles
resource "aws_iam_role_policy_attachment" "ml_api_execution_role_policy" {
  role       = aws_iam_role.ml_api_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Policy for ML API execution role to access SSM parameters
resource "aws_iam_policy" "ml_api_execution_role_ssm_policy" {
  name        = "${var.project_name}-${var.environment}-ml-api-ssm-policy"
  description = "Policy to allow ML API execution role to access SSM parameters"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "ssm:GetParameters",
          "ssm:GetParameter"
        ]
        Effect = "Allow"
        Resource = [
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.db_host_parameter_name}",
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.db_port_parameter_name}",
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.db_name_parameter_name}",
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.db_username_parameter_name}",
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.db_password_parameter_name}"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ml_api_execution_ssm_policy_attachment" {
  role       = aws_iam_role.ml_api_execution.name
  policy_arn = aws_iam_policy.ml_api_execution_role_ssm_policy.arn
}

# Policy for ML API task role to access SageMaker
resource "aws_iam_policy" "ml_api_task_policy" {
  name        = "${var.project_name}-${var.environment}-ml-api-task-policy"
  description = "Policy for ML API tasks"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Effect = "Allow"
        Resource = [
          "arn:aws:s3:::${var.s3_bucket_name}",
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      },
      {
        Action = [
          "sagemaker:InvokeEndpoint",
          "sagemaker:DescribeEndpoint",
          "sagemaker:DescribeEndpointConfig",
          "sagemaker:DescribeModel"
        ]
        Effect = "Allow"
        Resource = [
          "arn:aws:sagemaker:${var.aws_region}:${data.aws_caller_identity.current.account_id}:endpoint/${var.project_name}-${var.environment}-*",
          "arn:aws:sagemaker:${var.aws_region}:${data.aws_caller_identity.current.account_id}:endpoint-config/${var.project_name}-${var.environment}-*",
          "arn:aws:sagemaker:${var.aws_region}:${data.aws_caller_identity.current.account_id}:model/${var.project_name}-${var.environment}-*"
        ]
      },
      {
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Effect = "Allow"
        Resource = [
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.db_host_parameter_name}",
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.db_port_parameter_name}",
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.db_name_parameter_name}",
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.db_username_parameter_name}",
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.db_password_parameter_name}"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ml_api_task_policy_attachment" {
  role       = aws_iam_role.ml_api_task.name
  policy_arn = aws_iam_policy.ml_api_task_policy.arn
}

# Create an Application Load Balancer for ML API
resource "aws_lb" "ml_api" {
  name               = "${var.project_name}-${var.environment}-ml-api-alb"
  internal           = true  # Internal ALB since we'll expose via API Gateway
  load_balancer_type = "application"
  security_groups    = [var.app_security_group_id]
  subnets            = var.private_subnet_ids

  enable_deletion_protection = var.environment == "prod"

  tags = var.tags
}

# Create target group for ML API
resource "aws_lb_target_group" "ml_api" {
  name        = "${var.project_name}-${var.environment}-ml-api-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  
  health_check {
    enabled             = true
    interval            = 30
    path                = "/models"
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 3
    unhealthy_threshold = 3
    timeout             = 5
    matcher             = "200"
  }

  tags = var.tags
}

# Create HTTP listener for ML API
resource "aws_lb_listener" "ml_api_http" {
  load_balancer_arn = aws_lb.ml_api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ml_api.arn
  }
}

# Create task definition for ML API
resource "aws_ecs_task_definition" "ml_api" {
  family                   = "${var.project_name}-${var.environment}-ml-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ml_api_execution.arn
  task_role_arn            = aws_iam_role.ml_api_task.arn

  container_definitions = jsonencode([
    {
      name      = "${var.project_name}-${var.environment}-ml-api-container"
      image     = "${var.ecr_repository_url}:${var.image_tag}"
      essential = true
      
      portMappings = [
        {
          containerPort = 8080
          hostPort      = 8080
          protocol      = "tcp"
        }
      ]
      
      environment = [
        { name = "APP_ENV", value = var.environment },
        { name = "PORT", value = "8080" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "SAGEMAKER_ENDPOINT_PREFIX", value = "${var.project_name}-${var.environment}" },
        { name = "SAGEMAKER_ROLE_ARN", value = var.sagemaker_role_arn },
        { name = "USE_S3", value = "True" },
        { name = "S3_BUCKET", value = var.s3_bucket_name }
      ]
      
      secrets = [
        {
          name      = "DB_HOST"
          valueFrom = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.db_host_parameter_name}"
        },
        {
          name      = "DB_PORT"
          valueFrom = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.db_port_parameter_name}"
        },
        {
          name      = "DB_NAME"
          valueFrom = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.db_name_parameter_name}"
        },
        {
          name      = "DB_USER"
          valueFrom = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.db_username_parameter_name}"
        },
        {
          name      = "DB_PASSWORD"
          valueFrom = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.db_password_parameter_name}"
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.project_name}-${var.environment}-ml-api"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = var.tags
}

# Create ECS service for ML API
resource "aws_ecs_service" "ml_api" {
  name                               = "${var.project_name}-${var.environment}-ml-api-service"
  cluster                            = aws_ecs_cluster.ml_api.id
  task_definition                    = aws_ecs_task_definition.ml_api.arn
  desired_count                      = var.desired_count
  launch_type                        = "FARGATE"
  scheduling_strategy                = "REPLICA"
  health_check_grace_period_seconds  = 60
  force_new_deployment               = true

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.app_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.ml_api.arn
    container_name   = "${var.project_name}-${var.environment}-ml-api-container"
    container_port   = 8080
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = var.tags
}

# Create CloudWatch log group for ML API
resource "aws_cloudwatch_log_group" "ml_api_logs" {
  name              = "/ecs/${var.project_name}-${var.environment}-ml-api"
  retention_in_days = var.logs_retention_days

  tags = var.tags
}

# Set up auto-scaling for ML API
resource "aws_appautoscaling_target" "ml_api" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.ml_api.name}/${aws_ecs_service.ml_api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ml_api_cpu" {
  name               = "${var.project_name}-${var.environment}-ml-api-cpu-policy"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ml_api.resource_id
  scalable_dimension = aws_appautoscaling_target.ml_api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ml_api.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_policy" "ml_api_memory" {
  name               = "${var.project_name}-${var.environment}-ml-api-memory-policy"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ml_api.resource_id
  scalable_dimension = aws_appautoscaling_target.ml_api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ml_api.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# CloudWatch alarms for ML API
resource "aws_cloudwatch_metric_alarm" "ml_api_high_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-ml-api-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "60"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "High CPU utilization for ML API service"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
  
  dimensions = {
    ClusterName = aws_ecs_cluster.ml_api.name
    ServiceName = aws_ecs_service.ml_api.name
  }
}

resource "aws_cloudwatch_metric_alarm" "ml_api_high_memory" {
  alarm_name          = "${var.project_name}-${var.environment}-ml-api-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = "60"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "High memory utilization for ML API service"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
  
  dimensions = {
    ClusterName = aws_ecs_cluster.ml_api.name
    ServiceName = aws_ecs_service.ml_api.name
  }
}