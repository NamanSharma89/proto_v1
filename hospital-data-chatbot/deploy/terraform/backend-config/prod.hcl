bucket         = "myapp-terraform-state-prod"
key            = "prod/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "myapp-terraform-locks-prod"
encrypt        = true