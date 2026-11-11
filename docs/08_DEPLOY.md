# 08 · Execução e implantação

## Modo principal: local, na mesma rede do ESP32
Seu computador roda o backend + PostgreSQL; celular e ESP32 ficam na **mesma rede Wi‑Fi** (a arquitetura da equipe).
```bash
cp .env.example .env            # preencha POSTGRES_PASSWORD, ADMIN_API_KEY, ESP32_URL (IP do Monitor Serial)
docker compose up -d --build    # http://IP-DO-COMPUTADOR:8000  (abra no celular com esse IP)
```
Sem hardware: `docker compose --profile sim up -d --build` e `ESP32_URL=http://simulador:8081`. Sem Docker: `scripts/dev.sh`.
A demonstração funciona **sem internet** (Gemini cai no plano B; a recomendação de chuva mostra "sem dados"). **Docker não foi executado** ao construir este projeto: `docker compose build` pode exigir ajustes.

### Armadilhas de rede
- **Isolamento de clientes:** hotspots de celular e Wi‑Fi de visitantes costumam impedir dispositivos de se falarem. Teste `curl http://IP-DO-ESP32/` **do computador** antes. Se falhar, use um roteador seu.
- IP do ESP32 pode mudar (DHCP): reserve o IP no roteador.
- Firewall do computador: libere a porta 8000 para o celular acessar.
- Docker Desktop (Windows/macOS) alcança IPs da LAN normalmente; em Linux também (rede bridge com NAT).

## Nuvem (opcional): Terraform na AWS — leia o limite primeiro
**Um servidor na nuvem não alcança o ESP32 na sua rede local** (IP privado atrás de NAT). Então, na nuvem:
- `enable_simulator = true` (padrão): sobe junto o simulador do ESP32 (com modelo sintético, a menos que você coloque um modelo em `ai-model/models/current` antes de implantar). Serve para mostrar front, banco, histórico, painel e Gemini.
- Para usar o ESP32 de verdade a partir da nuvem é preciso uma VPN/túnel (ex.: Tailscale) até o ESP32 e `enable_simulator=false` com `esp32_url`. Não está montado nem testado.
- Recomendação para a apresentação: **local**. Use a nuvem só se a banca exigir uma URL pública.

### Como usar
```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars     # allowed_cidr = SEU IP /32; repo_url; senhas
terraform init && terraform plan && terraform apply
```
Cria: instância Ubuntu 24.04 (t3.small), Elastic IP, security group (porta 8000 só para `allowed_cidr`, IMDSv2, disco criptografado),
segredos no SSM Parameter Store (SecureString) lidos no boot, acesso por Session Manager (SSH opcional). O primeiro boot clona o repositório e roda o compose (alguns minutos; log em `/var/log/soiling-bootstrap.log`).
`terraform destroy` desfaz tudo (apague também o `terraform.tfstate`: ele contém os segredos).

### Limites honestos
- **Terraform não foi executado** aqui (só conferimos a sintaxe HCL com `python-hcl2`). Espere ajustes (nome da AMI, região, quotas).
- Só HTTP, sem TLS e sem domínio. Para HTTPS, coloque Caddy/nginx na frente (não incluído).
- `repo_url` precisa ser acessível sem credenciais (repositório público) ou ajustar o `user_data` para um token.
- Os segredos ficam no state do Terraform: guarde-o em local protegido.
- Custo: instância + IP + disco, cobrados enquanto existirem. Destrua depois da demonstração.
- Gemini na nuvem funciona (tem internet); a chave vem do SSM.
