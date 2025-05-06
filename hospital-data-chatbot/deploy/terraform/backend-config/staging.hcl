bucket         = "myapp-terraform-state-staging"
key            = "staging/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "myapp-terraform-locks-staging"
encrypt        = true