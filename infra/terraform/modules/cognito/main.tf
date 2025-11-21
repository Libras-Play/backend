# Cognito User Pool Module
locals { name = "${var.project_name}-${var.environment}" }

resource "aws_cognito_user_pool" "main" {
  name = "${local.name}-users"

  password_policy {
    minimum_length                   = var.password_minimum_length
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  # MFA deshabilitado (OFF) para dev - cambiar a OPTIONAL o ON en producción
  mfa_configuration = "OFF"

  auto_verified_attributes = ["email"]

  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true
  }

  tags = var.tags
}

resource "aws_cognito_user_pool_client" "main" {
  name         = "${local.name}-client"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret        = false
  refresh_token_validity = 30
  access_token_validity  = 60
  id_token_validity      = 60
  token_validity_units {
    refresh_token = "days"
    access_token  = "minutes"
    id_token      = "minutes"
  }

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]
}

resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${local.name}-auth"
  user_pool_id = aws_cognito_user_pool.main.id
}
