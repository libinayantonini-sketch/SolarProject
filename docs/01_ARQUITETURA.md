# 01 · Arquitetura

## Fluxo (1 análise), em um de dois modos
1. Usuário abre o front (celular ou PC), tira/escolhe a foto e escolhe **onde analisar**: ESP32 ou servidor.
2. O **front** reduz a foto para no máximo `UPLOAD_MAX_SIDE` px (padrão 512, sem esticar) e comprime em JPEG (`/api/config` informa os valores e quais modos estão disponíveis).
3. `POST /api/analyze` (multipart: `file`, `engine` = `esp32` (padrão) ou `server`, `pump`).
4. O **backend** valida o arquivo (≤ `MAX_UPLOAD_MB`, é imagem), corrige a orientação e guarda a foto normalizada. Depois:
   - **`esp32`**: gera o JPEG `ESP32_INPUT_SIZE`×`ESP32_INPUT_SIZE` (esticado, igual ao treino) e envia `POST {ESP32_URL}/upload?pump=0|1`.
     O ESP32 decodifica, quantiza, roda a rede, aplica a política da bomba e responde JSON (`05_PROTOCOLO_ESP32.md`).
   - **`server`**: o modelo grande (ONNX, `SERVER_MODEL_DIR`) classifica a foto no tamanho que ele espera. **Não há bomba.**
5. O backend valida o resultado, grava o JPEG em `STORAGE_DIR` e uma linha em `analyses` com o campo `engine` (se algo falhar, **nada** é gravado).
6. O front mostra motor, classe, confiança, bomba (só no ESP32) e tempos; histórico e painel se atualizam.

## Componentes
```
frontend (React) ── /api/* ──▶ backend (FastAPI)
                                 ├─ services/analysis.py   prepara imagem, orquestra
                                 ├─ services/esp32.py      cliente HTTP do ESP32 (valida a resposta e as classes)
                                 ├─ services/server_model.py modelo grande ONNX (opcional; nunca aciona a bomba)
                                 ├─ services/export.py     zip de fotos revisadas para retreino
                                 ├─ services/storage.py    arquivos (anti path traversal, gravação atômica)
                                 ├─ database/repository.py SQLAlchemy (PostgreSQL / SQLite)
                                 └─ services/assistant/    Gemini + plano B por regras
firmware (ESP32) ◀── HTTP local ── backend
```

## Falhas previstas
| Situação | Resposta da API | Efeito |
| --- | --- | --- |
| `ESP32_URL` vazio | 503 | nada gravado |
| ESP32 não responde (Wi‑Fi, IP, timeout) | 504 | nada gravado |
| ESP32 responde erro ou JSON fora do contrato (classe fora de `ESP32_CLASSES`, bomba > 60 s) | 502 | nada gravado |
| `engine=server` sem modelo na pasta `SERVER_MODEL_DIR` | 503 (o motivo vai na mensagem) | nada gravado; o modo ESP32 segue funcionando |
| Arquivo não é imagem / formato não suportado | 422 | nada gravado |
| Arquivo > limite | 413 | nada gravado |
| Sem `X-API-Key` com `pump=true` e chave configurada | 200, mas enviado `pump=0` e o front avisa | análise gravada, bomba bloqueada |
| Banco falha depois de gravar o arquivo | 500 | arquivo removido (sem órfão) |

## Concorrência
O ESP32 tem **um buffer só**: atende uma foto por vez. O backend espera a resposta na mesma requisição (timeout `ESP32_TIMEOUT_S`, 30 s).
Para a demonstração isso basta; se a inferência demorar demais, evoluir para processamento assíncrono com id de tarefa (não implementado).

## Segurança (nível protótipo)
Rede local confiável. `ADMIN_API_KEY` protege: acionar a bomba, corrigir rótulo, apagar. `ESP32_KEY` (opcional) é um segredo
compartilhado no cabeçalho `X-Device-Key`. **Não há TLS, nem login de usuários, nem limitação de taxa.** Não exponha à internet sem um proxy com HTTPS.
