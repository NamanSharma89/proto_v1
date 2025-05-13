# deploy/terraform/environments/stage.tfvars

environment         = "stage"
aws_region          = "ap-south-1"

# Network configuration
vpc_cidr            = "10.1.0.0/16"
availability_zones  = ["ap-south-1a", "ap-south-1b"]
enable_nat_gateway  = true

# Database configuration
db_instance_class   = "db.t3.small"
db_allocated_storage = 50

# Application deployment configuration
task_cpu            = 1024
task_memory         = 2048
desired_count       = 2
min_capacity        = 2
max_capacity        = 4

# Monitoring configuration
alarm_email         = "stage-alerts@yourdomain.com"

# ML configuration
enable_ml           = true