# deploy/terraform/modules/app_deployment/main.tf

# Add this to get the account ID
data "aws_caller_identity" "current" {}

# Create an ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = var.environment == "prod" ? "enabled" : "disabled"
  }

  tags = merge(
    {
      Name = "${var.project_name}-${var.environment}-cluster"
    },
    var.tags
  )
}

# Create a Task Definition
resource "aws_ecs_task_definition" "app" {
  family                   = "${var.project_name}-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

# Updated container definition in modules/app_deployment/main.tf
# (Only showing the modified part)

container_definitions = jsonencode([
  {
    name      = "${var.project_name}-${var.environment}-container"
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
      { name = "BEDROCK_MODEL_ID", value = "anthropic.claude-3-sonnet-20240229-v1:0" },
      { name = "USE_S3", value = "True" },
      { name = "S3_BUCKET", value = var.s3_bucket_name },
      { name = "AWS_REGION", value = var.aws_region }
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
        "awslogs-group"         = "/ecs/${var.project_name}-${var.environment}"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }
])

  tags = merge(
    {
      Name = "${var.project_name}-${var.environment}-task"
    },
    var.tags
  )
}

# Create IAM roles for ECS
resource "aws_iam_role" "ecs_execution" {
  name = "${var.project_name}-${var.environment}-ecs-execution-role"

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

  tags = merge(
    {
      Name = "${var.project_name}-${var.environment}-ecs-execution-role"
    },
    var.tags
  )
}

resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-${var.environment}-ecs-task-role"

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

  tags = merge(
    {
      Name = "${var.project_name}-${var.environment}-ecs-task-role"
    },
    var.tags
  )
}

# Attach policies to roles
resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Update in modules/app_deployment/main.tf

resource "aws_iam_policy" "app_policy" {
  name        = "${var.project_name}-${var.environment}-app-policy"
  description = "Policy for ${var.project_name} application"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          "arn:aws:s3:::${var.s3_bucket_name}",
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      },
      {
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      # Replace Secrets Manager permissions with SSM Parameter Store permissions
      {
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Effect   = "Allow"
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

resource "aws_iam_role_policy_attachment" "app_policy_attachment" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.app_policy.arn
}

# Create CloudWatch Logs group
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/ecs/${var.project_name}-${var.environment}"
  retention_in_days = var.environment == "prod" ? 30 : 7

  tags = merge(
    {
      Name = "${var.project_name}-${var.environment}-logs"
    },
    var.tags
  )
}

# Create ALB
resource "aws_lb" "app" {
  name               = "${var.project_name}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.app_security_group_id]
  subnets            = var.public_subnet_ids

  enable_deletion_protection = var.environment == "prod"

  tags = merge(
    {
      Name = "${var.project_name}-${var.environment}-alb"
    },
    var.tags
  )
}

resource "aws_lb_target_group" "app" {
  name        = "${var.project_name}-${var.environment}-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  
  health_check {
    enabled             = true
    interval            = 30
    path                = "/api/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 3
    unhealthy_threshold = 3
    timeout             = 5
    matcher             = "200"
  }

  tags = merge(
    {
      Name = "${var.project_name}-${var.environment}-tg"
    },
    var.tags
  )
}

# HTTP listener - always created
# Serves traffic directly if no HTTPS, redirects to HTTPS if certificate exists
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = local.use_https ? "redirect" : "forward"

    dynamic "redirect" {
      for_each = local.use_https ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }

    dynamic "forward" {
      for_each = local.use_https ? [] : [1]
      content {
        target_group {
          arn = aws_lb_target_group.app.arn
        }
      }
    }
  }
}

# HTTPS listener - only created if certificate ARN is provided
resource "aws_lb_listener" "https" {
  count = local.use_https ? 1 : 0
  
  load_balancer_arn = aws_lb.app.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# Create ECS Service
# Fixing the depends_on issue by using separate services based on HTTPS availability
resource "aws_ecs_service" "app_https" {
  count                             = local.use_https ? 1 : 0
  name                              = "${var.project_name}-${var.environment}-service"
  cluster                           = aws_ecs_cluster.main.id
  task_definition                   = aws_ecs_task_definition.app.arn
  desired_count                     = var.desired_count
  launch_type                       = "FARGATE"
  scheduling_strategy               = "REPLICA"
  health_check_grace_period_seconds = 60
  force_new_deployment              = true

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.app_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "${var.project_name}-${var.environment}-container"
    container_port   = 8080
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = merge(
    {
      Name = "${var.project_name}-${var.environment}-service"
    },
    var.tags
  )

  # Now using a direct resource reference, which is valid for depends_on
  depends_on = [aws_lb_listener.https[0]]
}

resource "aws_ecs_service" "app_http" {
  count                             = local.use_https ? 0 : 1
  name                              = "${var.project_name}-${var.environment}-service"
  cluster                           = aws_ecs_cluster.main.id
  task_definition                   = aws_ecs_task_definition.app.arn
  desired_count                     = var.desired_count
  launch_type                       = "FARGATE"
  scheduling_strategy               = "REPLICA"
  health_check_grace_period_seconds = 60
  force_new_deployment              = true

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.app_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "${var.project_name}-${var.environment}-container"
    container_port   = 8080
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = merge(
    {
      Name = "${var.project_name}-${var.environment}-service"
    },
    var.tags
  )

  # Using a direct resource reference, which is valid for depends_on
  depends_on = [aws_lb_listener.http]
}

# Auto-scaling
resource "aws_appautoscaling_target" "app" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${local.app_service_name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "app_cpu" {
  name               = "${var.project_name}-${var.environment}-cpu-policy"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.app.resource_id
  scalable_dimension = aws_appautoscaling_target.app.scalable_dimension
  service_namespace  = aws_appautoscaling_target.app.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_policy" "app_memory" {
  name               = "${var.project_name}-${var.environment}-memory-policy"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.app.resource_id
  scalable_dimension = aws_appautoscaling_target.app.scalable_dimension
  service_namespace  = aws_appautoscaling_target.app.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "service_high_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "60"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "High CPU utilization for ${var.project_name}-${var.environment} service"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
  
  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = local.app_service_name
  }
}

resource "aws_cloudwatch_metric_alarm" "service_high_memory" {
  alarm_name          = "${var.project_name}-${var.environment}-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = "60"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "High memory utilization for ${var.project_name}-${var.environment} service"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
  
  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = local.app_service_name
  }
}

# Add this policy for the ECS execution role in modules/app_deployment/main.tf

resource "aws_iam_policy" "ecs_execution_role_ssm_policy" {
  name        = "${var.project_name}-${var.environment}-ecs-ssm-policy"
  description = "Policy to allow ECS task execution role to access SSM parameters"

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

resource "aws_iam_role_policy_attachment" "ecs_execution_ssm_policy_attachment" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = aws_iam_policy.ecs_execution_role_ssm_policy.arn
}