# deploy/terraform/environments/backend-config/stage.hcl

bucket         = "hospital-data-chatbot-terraform-state-stage"
key            = "stage/terraform.tfstate"
region         = "ap-south-1"
dynamodb_table = "hospital-data-chatbot-terraform-locks-stage"
encrypt        = true