# deploy/terraform/environments/dev_cloud.tfvars

environment         = "dev_cloud"
aws_region          = "ap-south-1"

# Network configuration
vpc_cidr            = "10.0.0.0/16"
availability_zones  = ["ap-south-1a", "ap-south-1b"]
enable_nat_gateway  = false

# Database configuration
db_instance_class   = "db.t3.micro"
db_allocated_storage = 20

# Application deployment configuration
task_cpu            = 1024
task_memory         = 2048
desired_count       = 1
min_capacity        = 1
max_capacity        = 2

# Monitoring configuration
alarm_email         = "dev-alerts@yourdomain.com"

# ML configuration
enable_ml           = true