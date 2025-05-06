# Output values from the infrastructure deployment

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "web_security_group_id" {
  description = "ID of the web security group"
  value       = aws_security_group.web.id
}

output "web_server_public_ips" {
  description = "Public IP addresses of web servers"
  value       = aws_instance.web_servers[*].public_ip
}

output "web_server_private_ips" {
  description = "Private IP addresses of web servers"
  value       = aws_instance.web_servers[*].private_ip
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket for application assets"
  value       = aws_s3_bucket.app_assets.bucket
}

output "cloudwatch_alarm_names" {
  description = "Names of the CloudWatch alarms"
  value       = aws_cloudwatch_metric_alarm.high_cpu_alarm[*].alarm_name
}