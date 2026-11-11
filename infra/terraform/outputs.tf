output "url" {
  value       = "http://${aws_eip.app.public_ip}:8000"
  description = "Endereço do sistema (só responde ao CIDR permitido). O boot leva alguns minutos."
}

output "instance_id" {
  value       = aws_instance.app.id
  description = "Para acessar sem SSH: aws ssm start-session --target <id>"
}
