# Staging environment configuration

aws_region     = "us-east-1"
aws_account_id = "123456789012" # Replace with your AWS account ID
environment    = "staging"
project_name   = "myapp"

# Network configuration
vpc_cidr             = "10.1.0.0/16"
public_subnet_cidrs  = ["10.1.1.0/24", "10.1.2.0/24"]
private_subnet_cidrs = ["10.1.3.0/24", "10.1.4.0/24"]
availability_zones   = ["us-east-1a", "us-east-1b"]
enable_nat_gateway   = true

# Security configuration
web_ingress_cidr = ["0.0.0.0/0"]
ssh_ingress_cidr = ["10.0.0.0/16", "192.168.1.0/24"] # VPN or office IPs only

# Storage configuration
s3_versioning_enabled = true

# Compute configuration
web_instance_count       = 2
web_instance_type        = "t3.small"
web_instance_volume_size = 30
ec2_ami_id               = "ami-0c55b159cbfafe1f0" # Update this with current Amazon Linux 2 AMI
ssh_key_name             = "staging-key"

# Monitoring configuration
cpu_alarm_threshold   = 75
enable_sns_alerts     = true
alert_email_addresses = ["staging-alerts@example.com", "ops@example.com"]