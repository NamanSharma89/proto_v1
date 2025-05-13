# deploy/terraform/environments/prod.tfvars

environment         = "prod"
aws_region          = "ap-south-1"

# Network configuration
vpc_cidr            = "10.2.0.0/16"
availability_zones  = ["ap-south-1a", "ap-south-1b", "ap-south-1c"]
enable_nat_gateway  = true

# Database configuration
db_instance_class   = "db.t3.medium"
db_allocated_storage = 100

# Application deployment configuration
task_cpu            = 2048
task_memory         = 4096
desired_count       = 3
min_capacity        = 3
max_capacity        = 10

# Monitoring configuration
alarm_email         = "prod-alerts@yourdomain.com"

# ML configuration
enable_ml           = true