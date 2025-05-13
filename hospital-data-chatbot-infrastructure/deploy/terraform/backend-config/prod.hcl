# deploy/terraform/environments/backend-config/prod.hcl

bucket         = "hospital-data-chatbot-terraform-state-prod"
key            = "prod/terraform.tfstate"
region         = "ap-south-1"
dynamodb_table = "hospital-data-chatbot-terraform-locks-prod"
encrypt        = true