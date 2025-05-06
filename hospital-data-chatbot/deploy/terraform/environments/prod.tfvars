# Production environment configuration

aws_region     = "us-east-1"
aws_account_id = "123456789012" # Replace with your AWS account ID
environment    = "prod"
project_name   = "myapp"

# Network configuration
vpc_cidr             = "10.2.0.0/16"
public_subnet_cidrs  = ["10.2.1.0/24", "10.2.2.0/24", "10.2.3.0/24"]
private_subnet_cidrs = ["10.2.4.0/24", "10.2.5.0/24", "10.2.6.0/24"]
availability_zones   = ["us-east-1a", "us-east-1b", "us-east-1c"]
enable_nat_gateway   = true

# Security configuration
web_ingress_cidr = ["0.0.0.0/0"] # Consider using CloudFront and restricting this
ssh_ingress_cidr = ["10.0.0.0/8"] # VPN or bastion only

# Storage configuration
s3_versioning_enabled = true

# Compute configuration
web_instance_count       = 3
web_instance_type        = "t3.medium"
web_instance_volume_size = 50
ec2_ami_id               = "ami-0c55b159cbfafe1f0" # Update this with current Amazon Linux 2 AMI
ssh_key_name             = "prod-key"

# Monitoring configuration
cpu_alarm_threshold   = 70
enable_sns_alerts     = true
alert_email_addresses = ["prod-alerts@example.com", "ops@example.com", "oncall@example.com"]