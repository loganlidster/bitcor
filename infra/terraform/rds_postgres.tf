########################################
# Aurora PostgreSQL Serverless v2 (private subnets)
########################################

resource "aws_db_subnet_group" "aurora_pg_subnets" {
  name       = "${var.project_name}-pg-subnets"
  subnet_ids = aws_subnet.private[*].id
  tags = {
    Project     = var.project_name
    Environment = "prod"
  }
}

resource "aws_rds_cluster" "aurora_pg" {
  cluster_identifier          = "${var.project_name}-aurora-pg"
  engine                      = "aurora-postgresql"
  engine_mode                 = "provisioned"
  engine_version              = "15.4"
  database_name               = "bitcor"
  master_username             = "postgres"
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.aurora_pg_subnets.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]

  backup_retention_period      = 7
  preferred_backup_window      = "03:00-04:00"
  preferred_maintenance_window = "sun:04:00-sun:05:00"

  storage_encrypted = true

  serverlessv2_scaling_configuration {
    min_capacity = 0.5
    max_capacity = 2.0
  }

  tags = {
    Project     = var.project_name
    Environment = "prod"
  }

  depends_on = [aws_vpc.main, aws_subnet.private, aws_security_group.rds_sg]
}

resource "aws_rds_cluster_instance" "aurora_pg_instances" {
  count               = 2
  identifier          = "${var.project_name}-pg-instance-${count.index + 1}"
  cluster_identifier  = aws_rds_cluster.aurora_pg.id
  instance_class      = "db.serverless"
  engine              = aws_rds_cluster.aurora_pg.engine
  engine_version      = aws_rds_cluster.aurora_pg.engine_version
  publicly_accessible = false
  tags = {
    Project     = var.project_name
    Environment = "prod"
  }
}

output "aurora_pg_endpoint" {
  value = aws_rds_cluster.aurora_pg.endpoint
}
output "aurora_pg_reader_endpoint" {
  value = aws_rds_cluster.aurora_pg.reader_endpoint
}
output "aurora_pg_db_name" {
  value = aws_rds_cluster.aurora_pg.database_name
}
