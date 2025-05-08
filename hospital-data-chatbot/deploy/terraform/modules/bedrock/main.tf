# deploy/terraform/modules/bedrock/main.tf

resource "aws_iam_role" "bedrock_role" {
  name = "${var.project_name}-${var.environment}-bedrock-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    {
      Name = "${var.project_name}-${var.environment}-bedrock-role"
    },
    var.tags
  )
}

resource "aws_iam_policy" "bedrock_policy" {
  name        = "${var.project_name}-${var.environment}-bedrock-policy"
  description = "Policy for Amazon Bedrock access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-text-express-v1"
      },
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          "${var.s3_bucket_arn}",
          "${var.s3_bucket_arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "bedrock_policy_attachment" {
  role       = aws_iam_role.bedrock_role.name
  policy_arn = aws_iam_policy.bedrock_policy.arn
}

# Optional: Reference the foundation model details
data "aws_bedrock_foundation_model" "titan" {
  model_id = "amazon.titan-text-express-v1"
}