output "vpc_id" {
  description = "Complyra VPC ID"
  value       = aws_vpc.this.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.this.name
}

output "security_group_ids" {
  description = "Security groups for Complyra services"
  value = {
    alb      = aws_security_group.alb.id
    api      = aws_security_group.api.id
    web      = aws_security_group.web.id
    worker   = aws_security_group.worker.id
    rds      = aws_security_group.rds.id
    internal = aws_security_group.internal.id
  }
}

output "alb_dns_name" {
  description = "ALB DNS name — point your domain CNAME here"
  value       = aws_lb.app.dns_name
}

output "api_target_group_arn" {
  description = "API target group ARN"
  value       = aws_lb_target_group.api.arn
}

output "web_target_group_arn" {
  description = "Web target group ARN"
  value       = aws_lb_target_group.web.arn
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.postgres.address
}

output "ecs_service_names" {
  description = "ECS service names"
  value = {
    api    = aws_ecs_service.api.name
    worker = aws_ecs_service.worker.name
    web    = aws_ecs_service.web.name
    qdrant = aws_ecs_service.qdrant.name
    redis  = aws_ecs_service.redis.name
  }
}

output "service_discovery_endpoints" {
  description = "Cloud Map service discovery endpoints"
  value = {
    qdrant = "qdrant.internal:6333"
    redis  = "redis.internal:6379"
  }
}

output "ecs_task_execution_role_arn" {
  description = "ECS task execution role ARN"
  value       = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  description = "ECS task role ARN"
  value       = aws_iam_role.ecs_task.arn
}

output "jwt_secret_arn" {
  description = "Secrets Manager ARN for JWT secret"
  value       = aws_secretsmanager_secret.jwt.arn
}

output "sentry_secret_arn" {
  description = "Secrets Manager ARN for Sentry DSN if configured"
  value       = var.app_sentry_dsn != "" ? aws_secretsmanager_secret.sentry[0].arn : null
  sensitive   = true
}
