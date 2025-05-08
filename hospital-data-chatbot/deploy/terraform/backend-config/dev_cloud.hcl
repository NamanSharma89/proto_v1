# deploy/terraform/environments/backend-config/dev-cloud.hcl

bucket         = "hospital-data-chatbot-terraform-state-dev"
key            = "dev-cloud/terraform.tfstate"
region         = "ap-south-1"
dynamodb_table = "hospital-data-chatbot-terraform-locks-dev"
encrypt        = true