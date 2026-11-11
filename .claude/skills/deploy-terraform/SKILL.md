---
name: deploy-terraform
description: Executar localmente com Docker Compose ou implantar na AWS com Terraform, e explicar os limites de rede com o ESP32. Use ao subir o sistema, publicar ou diagnosticar rede.
---
# Execução e implantação

**Principal = local** (computador na mesma rede do ESP32): `cp .env.example .env` → `docker compose up -d --build` (ou `--profile sim` com o simulador). Sem Docker: `scripts/dev.sh`.
Docker e Terraform **não foram executados** ao construir o projeto.

**Nuvem é opcional e limitada:** um servidor na AWS **não alcança** o ESP32 na sua rede Wi‑Fi. Em `infra/terraform` o padrão sobe o **simulador** junto
(`enable_simulator=true`) para demonstrar front/banco/Gemini; usar o ESP32 real exige VPN/túnel (não montado).
`terraform.tfvars` (do exemplo) precisa de `allowed_cidr` (seu IP /32; 0.0.0.0/0 é recusado), `repo_url`, senhas. Segredos vão ao SSM e ficam também no state: proteja-o.
`terraform destroy` ao fim (custo). Sem TLS: não exponha à internet aberta.

Rede local — armadilhas: isolamento de clientes em hotspots (teste `curl http://IP-ESP32/` do computador), IP do ESP32 mutável (reserve no roteador), firewall na porta 8000.
