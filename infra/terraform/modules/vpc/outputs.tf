# =============================================================================
# VPC Module - Outputs
# =============================================================================

output "vpc_id" {
  description = "ID de la VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "CIDR block de la VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnets" {
  description = "IDs de subnets públicas"
  value       = aws_subnet.public[*].id
}

output "private_subnets" {
  description = "IDs de subnets privadas"
  value       = aws_subnet.private[*].id
}

output "database_subnets" {
  description = "IDs de subnets de base de datos"
  value       = aws_subnet.database[*].id
}

output "nat_gateway_ips" {
  description = "IPs públicas de NAT gateways"
  value       = aws_eip.nat[*].public_ip
}

output "internet_gateway_id" {
  description = "ID del Internet Gateway"
  value       = aws_internet_gateway.main.id
}

output "availability_zones" {
  description = "Lista de Availability Zones usadas"
  value       = local.azs
}
