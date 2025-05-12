#!/bin/bash
# deploy/terraform/terraform-secrets.sh
# Script to handle sensitive Terraform variables

# Set a secure database password for the environment
# This avoids storing the password in version control or passing it on the command line
export TF_VAR_db_password="YourComplex-Password123!"  # Change this to a secure password

# Add any other sensitive variables here
# export TF_VAR_another_secret="secret_value"

echo "Terraform secrets have been loaded into environment variables."
echo "Now you can run terraform-infra-manager.sh without exposing secrets on the command line."
echo "The password will be stored securely in AWS Parameter Store, not in Terraform state."