# Development environment configuration

aws_region     = "ap-south-1"
aws_account_id = "817019235550" # Replace with your AWS account ID
environment    = "dev"
project_name   = "hdc"

# Network configuration
vpc_cidr             = "10.0.0.0/16"
public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnet_cidrs = ["10.0.3.0/24", "10.0.4.0/24"]
availability_zones   = ["ap-south-1"]
enable_nat_gateway   = true

# Security configuration
web_ingress_cidr = ["0.0.0.0/0"] # Open to all in dev (not recommended for prod)
ssh_ingress_cidr = ["0.0.0.0/0"] # Restrict in higher environments

# Storage configuration
s3_versioning_enabled = true

# Compute configuration
web_instance_count       = 1
web_instance_type        = "t3.micro"
web_instance_volume_size = 20
ec2_ami_id               = "ami-0c55b159cbfafe1f0" # Update this with current Amazon Linux 2 AMI
ssh_key_name             = "dev-key"

# Monitoring configuration
cpu_alarm_threshold  = 80
enable_sns_alerts    = true
alert_email_addresses = ["naman.sharma89@gmail.com"]