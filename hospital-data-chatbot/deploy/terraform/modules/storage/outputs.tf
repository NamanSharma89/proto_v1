# deploy/terraform/modules/storage/outputs.tf

output "app_bucket_name" {
  description = "The name of the S3 bucket"
  value       = aws_s3_bucket.app_bucket.id
}

output "app_bucket_arn" {
  description = "The ARN of the S3 bucket"
  value       = aws_s3_bucket.app_bucket.arn
}

output "ecr_repository_url" {
  description = "The URL of the ECR repository"
  value       = aws_ecr_repository.app_repository.repository_url
}

output "ecr_repository_arn" {
  description = "The ARN of the ECR repository"
  value       = aws_ecr_repository.app_repository.arn
}