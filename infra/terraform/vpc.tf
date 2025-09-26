########################################
# Bitcor VPC + Subnets + SGs (us-west-1)
########################################

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs         = slice(data.aws_availability_zones.available.names, 0, 2)
  name_prefix = "${var.project_name}-net"

  vpc_cidr      = "10.0.0.0/16"
  public_cidrs  = ["10.0.1.0/24",  "10.0.2.0/24"]
  private_cidrs = ["10.0.101.0/24","10.0.102.0/24"]
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = local.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name        = "${local.name_prefix}-vpc"
    Project     = var.project_name
    Environment = "prod"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "${local.name_prefix}-igw"
    Project     = var.project_name
    Environment = "prod"
  }
}

# Public subnets (2)
resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  cidr_block              = local.public_cidrs[count.index]
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name        = "${local.name_prefix}-public-${count.index + 1}"
    Project     = var.project_name
    Environment = "prod"
    Tier        = "public"
  }
}

# Private subnets (2)
resource "aws_subnet" "private" {
  count = 2

  vpc_id            = aws_vpc.main.id
  cidr_block        = local.private_cidrs[count.index]
  availability_zone = local.azs[count.index]

  tags = {
    Name        = "${local.name_prefix}-private-${count.index + 1}"
    Project     = var.project_name
    Environment = "prod"
    Tier        = "private"
  }
}

# One EIP for single NAT (cost-aware)
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name        = "${local.name_prefix}-nat-eip"
    Project     = var.project_name
    Environment = "prod"
  }
}

# NAT Gateway in first public subnet
resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  depends_on    = [aws_internet_gateway.igw]

  tags = {
    Name        = "${local.name_prefix}-nat"
    Project     = var.project_name
    Environment = "prod"
  }
}

# Public route table -> IGW
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name        = "${local.name_prefix}-public-rt"
    Project     = var.project_name
    Environment = "prod"
  }
}

resource "aws_route_table_association" "public_assoc" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Private route table -> NAT
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat.id
  }

  tags = {
    Name        = "${local.name_prefix}-private-rt"
    Project     = var.project_name
    Environment = "prod"
  }
}

resource "aws_route_table_association" "private_assoc" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

#########################
# Security Groups
########################
