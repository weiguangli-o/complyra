variable "project_name" {
  description = "Project name prefix for created resources."
  type        = string
  default     = "complyra"
}

variable "aws_region" {
  description = "AWS region for deployment."
  type        = string
  default     = "ap-southeast-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the Complyra VPC."
  type        = string
  default     = "10.40.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones used by public and private subnets."
  type        = list(string)
  default     = ["ap-southeast-1a", "ap-southeast-1b"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets."
  type        = list(string)
  default     = ["10.40.1.0/24", "10.40.2.0/24"]
}


variable "acm_certificate_arn" {
  description = "ACM certificate ARN for HTTPS listener. Leave empty to keep HTTP only."
  type        = string
  default     = ""
}

variable "ecr_registry" {
  description = "ECR registry prefix (without repository name). Leave empty to auto-build from account and region."
  type        = string
  default     = ""
}

variable "image_tag" {
  description = "Container image tag for API/worker/web deployments."
  type        = string
  default     = "latest"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days for ECS services."
  type        = number
  default     = 14
}

variable "db_name" {
  description = "PostgreSQL database name."
  type        = string
  default     = "complyra"
}

variable "db_username" {
  description = "PostgreSQL admin username."
  type        = string
  default     = "app"
}

variable "db_password" {
  description = "PostgreSQL admin password. Replace before production apply."
  type        = string
  default     = "change-me-postgres-password"
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t3.medium"
}

variable "db_engine_version" {
  description = "PostgreSQL engine version."
  type        = string
  default     = "16.3"
}

variable "db_allocated_storage" {
  description = "Initial allocated storage (GiB) for RDS."
  type        = number
  default     = 100
}

variable "db_max_allocated_storage" {
  description = "Autoscaling max storage (GiB) for RDS."
  type        = number
  default     = 300
}

variable "db_multi_az" {
  description = "Whether RDS should run in Multi-AZ mode."
  type        = bool
  default     = true
}

variable "db_backup_retention_days" {
  description = "RDS backup retention in days. Free tier allows max 1 day."
  type        = number
  default     = 1
}

variable "db_backup_window" {
  description = "Preferred backup window in UTC."
  type        = string
  default     = "17:00-18:00"
}

variable "db_maintenance_window" {
  description = "Preferred maintenance window in UTC."
  type        = string
  default     = "sun:18:00-sun:19:00"
}

variable "db_deletion_protection" {
  description = "Enable deletion protection for RDS."
  type        = bool
  default     = true
}

variable "db_skip_final_snapshot" {
  description = "Skip final snapshot on destroy. Keep false in production."
  type        = bool
  default     = false
}

variable "db_apply_immediately" {
  description = "Apply RDS modifications immediately."
  type        = bool
  default     = false
}

variable "db_performance_insights_enabled" {
  description = "Enable RDS Performance Insights."
  type        = bool
  default     = true
}


variable "jwt_secret_value" {
  description = "Optional fixed JWT secret string. Leave empty to generate random value."
  type        = string
  default     = ""
  sensitive   = true
}

variable "app_sentry_dsn" {
  description = "Optional Sentry DSN that will be stored in Secrets Manager and injected into API tasks."
  type        = string
  default     = ""
  sensitive   = true
}

variable "app_env" {
  description = "Application environment value for APP_ENV."
  type        = string
  default     = "prod"
}

variable "app_log_level" {
  description = "Application log level."
  type        = string
  default     = "INFO"
}

variable "app_log_format" {
  description = "Application log format."
  type        = string
  default     = "json"
}

variable "app_cors_origins" {
  description = "Comma-separated CORS origins passed to APP_CORS_ORIGINS."
  type        = string
  default     = "https://app.example.com"
}

variable "app_trusted_hosts" {
  description = "Comma-separated trusted hosts passed to APP_TRUSTED_HOSTS."
  type        = string
  default     = "api.example.com,app.example.com"
}

variable "app_qdrant_url" {
  description = "Qdrant base URL. Uses Cloud Map service discovery by default."
  type        = string
  default     = "http://qdrant.internal:6333"
}

variable "app_llm_provider" {
  description = "LLM provider: gemini | openai | ollama."
  type        = string
  default     = "gemini"
}

variable "app_embedding_provider" {
  description = "Embedding provider: gemini | openai | sentence-transformers."
  type        = string
  default     = "gemini"
}

variable "app_gemini_api_key" {
  description = "Google Gemini API key."
  type        = string
  default     = ""
  sensitive   = true
}

variable "app_gemini_chat_model" {
  description = "Gemini chat model name."
  type        = string
  default     = "gemini-2.5-flash"
}

variable "app_gemini_embedding_model" {
  description = "Gemini embedding model name."
  type        = string
  default     = "gemini-embedding-001"
}

variable "app_embedding_dimension" {
  description = "Embedding vector dimension (768 for Gemini, 1536 for OpenAI, 384 for BGE)."
  type        = number
  default     = 768
}

variable "app_require_approval" {
  description = "Whether chat responses require approval workflow."
  type        = bool
  default     = true
}

variable "app_output_policy_enabled" {
  description = "Enable output policy guard in API workflow."
  type        = bool
  default     = true
}

variable "app_output_policy_block_patterns" {
  description = "Output policy regex patterns as JSON array."
  type        = string
  default     = "[\"AKIA[0-9A-Z]{16}\",\"ASIA[0-9A-Z]{16}\",\"(?:sk|rk)-[A-Za-z0-9]{20,}\"]"
}

variable "app_output_policy_block_message" {
  description = "Fallback message when output policy blocks a generated answer."
  type        = string
  default     = "The generated response was withheld due to policy checks. Please contact an administrator."
}


variable "api_task_cpu" {
  description = "Fargate CPU units for API task."
  type        = number
  default     = 1024
}

variable "api_task_memory" {
  description = "Fargate memory (MiB) for API task."
  type        = number
  default     = 2048
}

variable "worker_task_cpu" {
  description = "Fargate CPU units for worker task."
  type        = number
  default     = 1024
}

variable "worker_task_memory" {
  description = "Fargate memory (MiB) for worker task."
  type        = number
  default     = 2048
}

variable "web_task_cpu" {
  description = "Fargate CPU units for web task."
  type        = number
  default     = 512
}

variable "web_task_memory" {
  description = "Fargate memory (MiB) for web task."
  type        = number
  default     = 1024
}

variable "api_desired_count" {
  description = "Desired count for API ECS service."
  type        = number
  default     = 2
}

variable "worker_desired_count" {
  description = "Desired count for worker ECS service."
  type        = number
  default     = 1
}

variable "web_desired_count" {
  description = "Desired count for web ECS service."
  type        = number
  default     = 2
}

variable "enable_synthetics" {
  description = "Create CloudWatch Synthetics canary resources."
  type        = bool
  default     = true
}

variable "synthetics_artifacts_force_destroy" {
  description = "Allow Terraform destroy to remove synthetics artifact bucket even when not empty."
  type        = bool
  default     = true
}

variable "synthetics_runtime_version" {
  description = "CloudWatch Synthetics runtime version."
  type        = string
  default     = "syn-nodejs-puppeteer-8.0"
}

variable "synthetics_start_canary" {
  description = "Start canary automatically after creation."
  type        = bool
  default     = false
}

variable "synthetics_schedule_expression" {
  description = "Canary schedule expression."
  type        = string
  default     = "rate(5 minutes)"
}

variable "synthetics_timeout_seconds" {
  description = "Canary timeout in seconds."
  type        = number
  default     = 60
}

variable "synthetics_memory_in_mb" {
  description = "Canary memory in MB."
  type        = number
  default     = 960
}

variable "synthetics_active_tracing" {
  description = "Enable active X-Ray tracing for canary runs."
  type        = bool
  default     = true
}

variable "synthetics_success_retention_days" {
  description = "Retention period (days) for successful canary runs."
  type        = number
  default     = 14
}

variable "synthetics_failure_retention_days" {
  description = "Retention period (days) for failed canary runs."
  type        = number
  default     = 30
}

variable "synthetics_api_base_url" {
  description = "API base URL used by the canary."
  type        = string
  default     = "https://api.example.com"
}

variable "synthetics_username" {
  description = "Username used by canary login step."
  type        = string
  default     = "demo"
}

variable "synthetics_password" {
  description = "Password used by canary login step."
  type        = string
  default     = "demo123"
  sensitive   = true
}

variable "synthetics_tenant_id" {
  description = "Tenant header used by canary chat request."
  type        = string
  default     = "default"
}

variable "synthetics_check_question" {
  description = "Question payload used by canary chat check."
  type        = string
  default     = "Please provide the latest policy summary."
}
