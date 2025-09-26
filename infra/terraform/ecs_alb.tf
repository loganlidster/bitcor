########################################
# ALB + ECS services (API + Engine)
########################################

# Region convenience var (defaults to us-west-1)
variable "aws_region" {
  type        = string
  default     = "us-west-1"
  description = "Region for ECR URLs and logs"
}

data "aws_caller_identity" "current" {}

locals {
  name_prefix  = var.project_name
  cluster_name = "bitcor-cluster"
  api_name     = "${local.name_prefix}-api"
  engine_name  = "${local.name_prefix}-engine"
  api_port     = 8080

  ecr_registry = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com"
  api_image    = "${local.ecr_registry}/v7-api:latest"
  engine_image = "${local.ecr_registry}/v7-engine:latest"
}

####################
# IAM Roles
####################

resource "aws_iam_role" "ecs_task_execution" {
  name = "${local.name_prefix}-ecs-task-exec"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "ecs-tasks.amazonaws.com" },
      Action = "sts:AssumeRole"
    }]
  })
  tags = { Project = var.project_name, Environment = "prod" }
}

resource "aws_iam_role_policy_attachment" "ecs_task_exec_policy" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task_role" {
  name = "${local.name_prefix}-ecs-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "ecs-tasks.amazonaws.com" },
      Action = "sts:AssumeRole"
    }]
  })
  tags = { Project = var.project_name, Environment = "prod" }
}

####################
# ALB (HTTP for now)
####################

resource "aws_lb" "api" {
  name               = "${local.name_prefix}-alb"
  load_balancer_type = "application"
  internal           = false
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = aws_subnet.public[*].id
  tags               = { Project = var.project_name, Environment = "prod" }
}

resource "aws_lb_target_group" "api" {
  name     = "${local.name_prefix}-tg"
  port     = local.api_port
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    path                = "/healthz"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 5
    matcher             = "200"
  }

  tags = { Project = var.project_name, Environment = "prod" }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

##########################
# Task Definitions
##########################

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${local.api_name}"
  retention_in_days = 7
  tags              = { Project = var.project_name, Environment = "prod" }
}

resource "aws_cloudwatch_log_group" "engine" {
  name              = "/ecs/${local.engine_name}"
  retention_in_days = 7
  tags              = { Project = var.project_name, Environment = "prod" }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${local.api_name}-td"
  cpu                      = "256"
  memory                   = "512"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = local.api_name
      image     = local.api_image
      essential = true
      portMappings = [{
        containerPort = local.api_port
        hostPort      = local.api_port
        protocol      = "tcp"
      }]
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8080/healthz || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 10
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-region        = var.aws_region
          awslogs-group         = "/ecs/${local.api_name}"
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = { Project = var.project_name, Environment = "prod" }
}

resource "aws_ecs_task_definition" "engine" {
  family                   = "${local.engine_name}-td"
  cpu                      = "256"
  memory                   = "512"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = local.engine_name
      image     = local.engine_image
      essential = true
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-region        = var.aws_region
          awslogs-group         = "/ecs/${local.engine_name}"
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = { Project = var.project_name, Environment = "prod" }
}

##########################
# Services
##########################

resource "aws_ecs_service" "api" {
  name            = "${local.api_name}-svc"
  cluster         = aws_ecs_cluster.core.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.ecs_sg.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = local.api_name
    container_port   = local.api_port
  }

  depends_on = [aws_lb_listener.http]
  tags       = { Project = var.project_name, Environment = "prod" }
}

resource "aws_ecs_service" "engine" {
  name            = "${local.engine_name}-svc"
  cluster         = aws_ecs_cluster.core.id
  task_definition = aws_ecs_task_definition.engine.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.ecs_sg.id]
    assign_public_ip = false
  }

  tags = { Project = var.project_name, Environment = "prod" }
}

##########################
# Outputs
##########################

output "alb_dns_name" {
  value = aws_lb.api.dns_name
}
