# deploy/terraform/modules/database/main.tf

resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-db-subnet-group"
  subnet_ids = var.subnet_ids

  tags = {
    Name = "${var.project_name}-${var.environment}-db-subnet-group"
  }
}

# Add this data source to fetch password from Parameter Store
data "aws_ssm_parameter" "db_password" {
  name = var.db_password_parameter_name
}

resource "aws_db_instance" "postgres" {
  identifier           = "${var.project_name}-${var.environment}"
  engine               = "postgres"
  engine_version       = "14"
  instance_class       = var.instance_class
  allocated_storage    = var.allocated_storage
  storage_type         = "gp3"
  
  db_name              = var.db_name
  username             = var.username
  password             = data.aws_ssm_parameter.db_password.value
  
  vpc_security_group_ids = [var.security_group_id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  multi_az               = var.environment == "prod"
  backup_retention_period = var.environment == "prod" ? 7 : 1
  deletion_protection    = var.environment == "prod"
  skip_final_snapshot    = var.environment != "prod"
  
  parameter_group_name = aws_db_parameter_group.postgres.name
  
  tags = {
    Name = "${var.project_name}-${var.environment}-postgres"
  }
}

resource "aws_db_parameter_group" "postgres" {
  name   = "${var.project_name}-${var.environment}-pg-params"
  family = "postgres14"

  parameter {
    name  = "log_statement"
    value = var.environment == "prod" ? "none" : "ddl"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = var.environment == "prod" ? "1000" : "100"
  }
}

# Store the connection information in SSM Parameter Store (instead of Secrets Manager)
resource "aws_ssm_parameter" "db_host" {
  name        = "/${var.project_name}/${var.environment}/db-host"
  description = "Database hostname for ${var.project_name} ${var.environment}"
  type        = "String"
  value       = aws_db_instance.postgres.address
  
  tags = {
    Name = "${var.project_name}-${var.environment}-db-host"
  }
}

resource "aws_ssm_parameter" "db_port" {
  name        = "/${var.project_name}/${var.environment}/db-port"
  description = "Database port for ${var.project_name} ${var.environment}"
  type        = "String"
  value       = aws_db_instance.postgres.port
  
  tags = {
    Name = "${var.project_name}-${var.environment}-db-port"
  }
}

resource "aws_ssm_parameter" "db_name" {
  name        = "/${var.project_name}/${var.environment}/db-name"
  description = "Database name for ${var.project_name} ${var.environment}"
  type        = "String"
  value       = var.db_name
  
  tags = {
    Name = "${var.project_name}-${var.environment}-db-name"
  }
}

resource "aws_ssm_parameter" "db_username" {
  name        = "/${var.project_name}/${var.environment}/db-username"
  description = "Database username for ${var.project_name} ${var.environment}"
  type        = "String"
  value       = var.username
  
  tags = {
    Name = "${var.project_name}-${var.environment}-db-username"
  }
}

# We don't need to create a password parameter here since it's already managed
# by our script and accessed via the data source above