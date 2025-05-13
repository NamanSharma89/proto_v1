# deploy/terraform/modules/storage/main.tf

# S3 bucket for application data
resource "aws_s3_bucket" "app_bucket" {
  bucket = "${var.project_name}-${var.environment}-data"
  
  tags = merge(
    {
      Name = "${var.project_name}-${var.environment}-data"
    },
    var.tags
  )
}

# Enable versioning on the S3 bucket
resource "aws_s3_bucket_versioning" "app_bucket_versioning" {
  bucket = aws_s3_bucket.app_bucket.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption for the S3 bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "app_bucket_encryption" {
  bucket = aws_s3_bucket.app_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ECR repository for Docker images
resource "aws_ecr_repository" "app_repository" {
  name = "${var.project_name}-${var.environment}"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  tags = merge(
    {
      Name = "${var.project_name}-${var.environment}-repository"
    },
    var.tags
  )
}

# ECR lifecycle policy (keep only the latest 10 images)
resource "aws_ecr_lifecycle_policy" "app_repository_policy" {
  repository = aws_ecr_repository.app_repository.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only the latest 10 images"
        selection = {
          tagStatus     = "any"
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}