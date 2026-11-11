variable "region" {
  type        = string
  default     = "sa-east-1"
  description = "Região AWS (sa-east-1 = São Paulo)."
}

variable "name" {
  type        = string
  default     = "soiling-detection"
  description = "Prefixo dos recursos."
}

variable "instance_type" {
  type        = string
  default     = "t3.small"
  description = "Tipo da instância. A API não roda modelo, então t3.small basta para a demonstração."
}

variable "allowed_cidr" {
  type        = string
  description = "Quem pode acessar a API (CIDR). Use o SEU IP, ex.: 203.0.113.10/32. Não há valor padrão de propósito: evite 0.0.0.0/0."
  validation {
    condition     = can(cidrhost(var.allowed_cidr, 0)) && var.allowed_cidr != "0.0.0.0/0"
    error_message = "Informe um CIDR válido e diferente de 0.0.0.0/0."
  }
}

variable "ssh_key_name" {
  type        = string
  default     = ""
  description = "Nome de um key pair existente para SSH. Vazio = sem SSH (use o Session Manager)."
}

variable "repo_url" {
  type        = string
  description = "URL Git (https) do repositório do projeto, clonado na instância."
}

variable "repo_ref" {
  type        = string
  default     = "main"
  description = "Branch ou tag a implantar."
}

variable "admin_api_key" {
  type        = string
  sensitive   = true
  description = "Chave de administrador da API (ADMIN_API_KEY)."
}

variable "postgres_password" {
  type        = string
  sensitive   = true
  description = "Senha do PostgreSQL."
}

variable "gemini_api_key" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Opcional. Chave da API do Gemini."
}

variable "gemini_model" {
  type        = string
  default     = ""
  description = "Nome do modelo Gemini (confira na documentação do Google; os nomes mudam)."
}

variable "enable_simulator" {
  type        = bool
  default     = true
  description = "Sobe o simulador do ESP32 junto. Na nuvem NÃO há como alcançar um ESP32 na sua rede Wi-Fi, então o simulador é o que permite demonstrar o fluxo."
}

variable "esp32_url" {
  type        = string
  default     = ""
  description = "Só se você tiver uma VPN/túnel (ex.: Tailscale) até o ESP32. Ignorado quando enable_simulator = true."
}

variable "volume_gb" {
  type    = number
  default = 20
}
