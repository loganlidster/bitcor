########################################
# Cognito User Pool + Client + Domain
########################################

resource "aws_cognito_user_pool" "pool" {
  name = "${var.project_name}-user-pool"
  username_attributes = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }

  tags = {
    Project     = var.project_name
    Environment = "prod"
  }
}

resource "aws_cognito_user_pool_client" "client" {
  name         = "${var.project_name}-app-client"
  user_pool_id = aws_cognito_user_pool.pool.id

  generate_secret = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows  = ["code"]
  allowed_oauth_scopes = ["email", "openid", "profile"]
  callback_urls        = ["http://localhost:3000/callback"]
  logout_urls          = ["http://localhost:3000/logout"]
  supported_identity_providers = ["COGNITO"]

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_USER_PASSWORD_AUTH"
  ]
}

resource "aws_cognito_user_pool_domain" "domain" {
  domain       = "${var.project_name}-auth-${substr(md5(var.project_name),0,6)}"
  user_pool_id = aws_cognito_user_pool.pool.id
}

output "cognito_user_pool_id"   { value = aws_cognito_user_pool.pool.id }
output "cognito_app_client_id"  { value = aws_cognito_user_pool_client.client.id }
output "cognito_hosted_domain"  { value = aws_cognito_user_pool_domain.domain.domain }
