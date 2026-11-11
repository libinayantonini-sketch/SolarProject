data "aws_vpc" "default" {
  default = true
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
}

locals {
  esp32_url = var.enable_simulator ? "http://simulador:8081" : var.esp32_url
  ssm_path  = "/${var.name}"
}

# ---- segredos no SSM Parameter Store (a instância os lê no boot; não vão no user_data) ----
# Atenção: os valores também ficam no terraform.tfstate. Proteja/guarde o state com cuidado (docs/08_DEPLOY_TERRAFORM.md).
resource "aws_ssm_parameter" "admin_api_key" {
  name  = "${local.ssm_path}/ADMIN_API_KEY"
  type  = "SecureString"
  value = var.admin_api_key
}

resource "aws_ssm_parameter" "postgres_password" {
  name  = "${local.ssm_path}/POSTGRES_PASSWORD"
  type  = "SecureString"
  value = var.postgres_password
}

resource "aws_ssm_parameter" "gemini_api_key" {
  count = var.gemini_api_key == "" ? 0 : 1
  name  = "${local.ssm_path}/GEMINI_API_KEY"
  type  = "SecureString"
  value = var.gemini_api_key
}

# ---- identidade da instância ----
data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app" {
  name               = "${var.name}-ec2"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore" # Session Manager: acesso sem abrir SSH
}

data "aws_iam_policy_document" "read_params" {
  statement {
    actions   = ["ssm:GetParameter", "ssm:GetParametersByPath"]
    resources = ["arn:aws:ssm:${var.region}:*:parameter${local.ssm_path}/*"]
  }
}

resource "aws_iam_role_policy" "read_params" {
  name   = "read-params"
  role   = aws_iam_role.app.id
  policy = data.aws_iam_policy_document.read_params.json
}

resource "aws_iam_instance_profile" "app" {
  name = "${var.name}-ec2"
  role = aws_iam_role.app.name
}

# ---- rede ----
resource "aws_security_group" "app" {
  name        = "${var.name}-sg"
  description = "API do Soiling Detection"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "API e front (HTTP 8000) somente do CIDR permitido"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  dynamic "ingress" {
    for_each = var.ssh_key_name == "" ? [] : [1]
    content {
      description = "SSH somente do CIDR permitido"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [var.allowed_cidr]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---- servidor ----
resource "aws_instance" "app" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  iam_instance_profile   = aws_iam_instance_profile.app.name
  vpc_security_group_ids = [aws_security_group.app.id]
  key_name               = var.ssh_key_name == "" ? null : var.ssh_key_name

  metadata_options {
    http_tokens = "required" # IMDSv2
  }

  root_block_device {
    volume_size = var.volume_gb
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    region        = var.region
    ssm_path      = local.ssm_path
    repo_url      = var.repo_url
    repo_ref      = var.repo_ref
    esp32_url     = local.esp32_url
    gemini_model  = var.gemini_model
    use_gemini    = var.gemini_api_key != ""
    use_simulator = var.enable_simulator
  })
  user_data_replace_on_change = true

  tags = { Name = var.name }

  depends_on = [aws_ssm_parameter.admin_api_key, aws_ssm_parameter.postgres_password]
}

resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"
}
