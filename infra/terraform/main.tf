terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Empty backend; values injected by workflow (-backend-config flags)
  backend "s3" {}
}

provider "aws" { region = "us-west-1" }

variable "project_name" {
  type        = string
  default     = "bitcor"
  description = "Project name for tagging"
}

# Minimal infra so you can see resources immediately

resource "aws_ecr_repository" "api" {
  name                 = "v7-api"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  tags = { Project = var.project_name, Environment = "prod" }
}

resource "aws_ecr_repository" "engine" {
  name                 = "v7-engine"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  tags = { Project = var.project_name, Environment = "prod" }
}

resource "aws_ecs_cluster" "core" {
  name = "bitcor-cluster"
  tags = { Project = var.project_name, Environment = "prod" }
}
