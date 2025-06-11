# This file is used for testing the terraform-ls Language Server functionality
# It's a simple Terraform configuration with common resource types

# Configure the AWS Provider
provider "aws" {
  region = "us-west-2"
}

# Variables for testing
variable "instance_type" {
  description = "The EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "terry-form-test"
}

# Resource for testing hover functionality
resource "aws_instance" "example" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = var.instance_type
  
  tags = {
    Name        = "${var.project_name}-instance"
    Environment = "testing"
  }
}

# Resource for testing completion functionality
resource "aws_s3_bucket" "example" {
  bucket = "${var.project_name}-${terraform.workspace}-bucket"
  
  tags = {
    Name        = "${var.project_name}-bucket"
    Environment = terraform.workspace
  }
}

# Output for testing
output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.example.id
}

# Missing closing curly brace to test validation functionality
