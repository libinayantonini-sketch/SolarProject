# Histórico do projeto até a mudança de rumo (5 nov 2026)

> **Só documentação.** Nada daqui é código para reaproveitar. Em 5/11/2026 a equipe mudou o escopo: o projeto agora **apenas classifica**
> sujeira (LIMPO / MODERADO / SEVERO) e aciona uma bomba pelo ESP32. Perda de potência, R$, pvlib, Open‑Meteo, PLD e motor de decisão por custo
> **saíram do projeto**. Este arquivo registra o que existiu, o que foi aprendido e por que cada parte saiu, para a banca e para a memória da equipe.

## Linha do tempo
| Data | O que aconteceu |
| --- | --- |
| 30/10 | A equipe perguntou sobre o modelo de um notebook (DeepSolarEye): se era "forte", se era convolucional e o que ele faz com a imagem. Foi explicado que é uma **rede convolucional (CNN)** e que o treino era de **regressão**: a rede produz **um número** a partir da imagem e o treino aproxima esse número do valor **L** que vem no nome do arquivo (perda de geração por sujeira, medida). Discutiu‑se por que um número da rede pode ser comparado a L: a rede é treinada para minimizar a diferença entre os dois (erro entre previsto e L); não há "cálculo" separado. |
| 3/11 | Pedido de um protótipo de front‑end (dashboards, parte financeira com "vale a pena limpar?", histórico). Surgiu o app **Soiling Intelligence**. |
| 3/11 | Notebook `DeepSolarEye_Training.ipynb` convertido para **carregamento preguiçoso** (lazy loading das imagens, para não estourar a memória). |
| 3/11 (noite) | Tela mais limpa; decidiu‑se usar a **API Open‑Meteo** (chuva e radiação). |
| 4/11 | Decisão de montar o front primeiro, depois o back‑end, com skills para Claude Code, banco (a definir), preço da energia, **pvlib** e IA (Grok ou Gemini) para resumos. Entregue um zip com app, API, testes e skills. |
| 9/11 | Open‑Meteo voltou **só como recomendação de chuva na tela** (sem R$, sem pvlib, sem influenciar a bomba). |
| 5/11 | **Mudança de rumo**: só classificação de 3 níveis, dataset Roboflow, PostgreSQL, front com upload, Gemini no front, ESP32 + bomba. |
| 5/11 | Chegou o **documento de arquitetura do protótipo**: inferência embarcada no ESP32, HTTP local, React+TS+Tailwind+Recharts, FastAPI, imagens em arquivos. O projeto foi refeito sobre ele. |

## O que existiu na fase anterior (Soiling Intelligence)
Para cada bloco de uma usina, recomendar **limpar hoje, aguardar, monitorar ou conferir a foto**, comparando o custo de esperar com o custo de limpar em R$.
- **Regra de decisão** em módulo puro (`decision/engine.py`), com unidades fixas: perda em fração 0–1, energia em MWh, preço em R$/MWh, chuva em mm/dia.
- **Open‑Meteo** (chuva diária e irradiância horária) e **pvlib** (geração esperada com o painel limpo; modelo PVWatts) — fórmula da proposta: *perda do dia (R$) = geração esperada (MWh) × perda por sujeira × preço (R$/MWh)*.
- **Preço da energia**: cenários (R$ 120/230/380 por MWh, premissas) e parser do PLD horário da CCEE (colunas do CSV nunca confirmadas).
- **IA para resumo semanal** (Gemini/Grok), com validação que descartava número inventado e texto determinístico como plano B.
- **API FastAPI v1** com SQLite, 57 testes sem internet, contrato OpenAPI, protótipo visual em HTML e um dashboard publicado como artefato.
- Estado honesto da época: Open‑Meteo e Gemini **nunca foram chamados de verdade**; coordenadas, kWp e taxas de acúmulo eram valores de exemplo.

## Fatos verificados naquela fase (úteis ainda hoje)
- **Dataset Roboflow** `amr-fph1m/solar-panel-dust-and-soiling`: ≈2,3 mil imagens, classes Clean/Dusty/Soiled, **CC BY 4.0** (citar a fonte). Tipo do projeto (classificação × detecção) não confirmado.
- **Gemini**: há plano gratuito pelo Google AI Studio segundo buscas; **limites oficiais não verificados** (a página não carregou) e termos de uso de dados no plano gratuito pendentes. O nome do modelo **não** deve ser fixado no código.
- **Grok (xAI)**: documentação oficial listava só preços pagos; descartado em favor do Gemini (gratuito).
- **PLD (CCEE)**: dataset `pld_horario`, CSV por ano e submercado, CC‑BY‑4.0, atualizado diariamente; nomes de colunas não confirmados.
- pvlib 0.16.1 funcionou localmente; no semiárido, ~7,75 MWh/dia em céu claro para um bloco de 1,5 MWp.
- Ambiente de construção sem acesso a vários sites (Open‑Meteo, docs do Gemini): nenhuma integração externa foi testada contra o serviço real.

## Por que cada peça saiu
| Peça | Motivo |
| --- | --- |
| Regressão da perda (L) e R$ | o objetivo virou **classificar em 3 níveis** e acionar uma bomba; não há medição de perda no protótipo |
| Open‑Meteo, pvlib, PLD, motor de custo | dependiam da perda em R$; o protótipo não calcula valor financeiro |
| Notebook com lazy load (PyTorch) | o novo caminho é Keras → TFLite int8 para o ESP32; imagens são pequenas (96×96) e cabem na memória após o resize |
| SQLite | PostgreSQL pedido; SQLite continua só nos testes |
| Resumo semanal da IA | virou assistente de busca/resumo sobre as análises (Gemini com plano B) |
| Inferência no servidor (ONNX), tokens de dispositivo e fila de comandos da bomba (desenhados em 5/11 antes do documento de arquitetura) | o documento define **inferência no ESP32** e HTTP local simples; o servidor só encaminha e registra |

## O que foi mantido como ideia
- **Plano B determinístico** para a IA e validação de números do resumo.
- **Humano na decisão**: correção de rótulo por pessoa (`human_label`) sem apagar o que o modelo disse.
- Rotular tudo que é simulado; dado ausente é nulo, nunca preenchido em silêncio; não dizer que algo foi testado sem ter rodado.

## Artefatos antigos (se ainda existirem na sua máquina)
Pasta `soiling-intelligence-app/` e o zip da fase anterior; dashboard publicado como artefato; `DeepSolarEye_Training_lazy.ipynb`. **Não fazem parte deste repositório.**

## 10/11 · Modo servidor (modelo grande) volta, como segundo modo
A equipe decidiu ter **dois modos** de análise: ESP32 (na hora, decide a bomba) e **modelo grande no servidor** (ONNX, ex.: ResNet; nunca aciona a bomba).
Não haverá modo "comparar". Tamanhos de entrada e classes são configuração: `ESP32_INPUT_SIZE`, `SERVER_INPUT_SIZE`, `ESP32_CLASSES`, `labels.json`.
O ESP32 pode passar a ter 2 classes (LIMPO/SEVERO); o modelo grande fica com 3. O dataset não entra no repositório: só o modelo treinado e as fotos novas
(exportação para retreino). O servidor roda localmente. Detalhes: `docs/12_MODELO_NO_SERVIDOR.md`. Este modo se aplica **ao lado** da decisão de 5/11, não a substitui.
