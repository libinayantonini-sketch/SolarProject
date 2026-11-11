"""Assistente: a IA traduz a pergunta em filtro e redige o resumo; o BANCO busca e conta.

Garantias:
- a IA nunca recebe fotos nem escolhe fotos: só vê contagens agregadas;
- o filtro devolvido pela IA passa por validação (pydantic); inválido => regras em português;
- o resumo só é aceito se todo número citado existir nos dados enviados; senão usamos texto determinístico;
- qualquer falha da IA (rede, cota, resposta ruim) cai no plano B, sempre sinalizado em `fonte`.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

from pydantic import ValidationError

from app.services.assistant.search import SearchFilter, describe_filter, rule_based_filter
from app.services.assistant.gemini import GeminiClient, GeminiError

SYSTEM_FILTER = (
    "Você converte perguntas em português sobre análises de fotos de painéis solares em um filtro JSON. "
    "Classes possíveis: LIMPO, MODERADO, SEVERO. Campos opcionais: labels (lista de classes), since e until "
    "(ISO 8601 com fuso), needs_review (bool: fotos de baixa confiança sem revisão), min_confidence e "
    "max_confidence (0 a 1), cleaning_activated (bool: a bomba foi acionada), text (trecho do nome do arquivo). "
    "Responda SOMENTE o objeto JSON; omita campos que a pergunta não menciona. Não invente filtros."
)
SYSTEM_SUMMARY = (
    "Você escreve resumos curtos (no máximo 4 frases) em português sobre classificação de sujeira em painéis solares. "
    "Use APENAS os números fornecidos; não calcule porcentagens nem cite valores que não estejam nos dados. "
    "Não dê recomendações de manutenção além de sugerir revisar fotos marcadas para revisão."
)


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?", text))


def _allowed_numbers(payload: dict) -> set[str]:
    out: set[str] = set()
    for n in _numbers(json.dumps(payload, ensure_ascii=False, default=str)):
        out.add(n)
        out.add(n.replace(".", ","))
    return out


def deterministic_summary(question: str, f: SearchFilter, total: int, stats: dict) -> str:
    por = stats["por_rotulo"]
    parts = [f"Encontrei {total} análise(s) para: {describe_filter(f)}."]
    parts.append(f"No histórico inteiro: {stats['total']} análises — {por['LIMPO']} limpas, {por['MODERADO']} moderadas, {por['SEVERO']} severas.")
    if stats["para_revisao"]:
        parts.append(f"{stats['para_revisao']} análise(s) com baixa confiança aguardam revisão humana.")
    return " ".join(parts)


class Assistant:
    def __init__(self, client: GeminiClient | None) -> None:
        self.client = client

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def interpret(self, question: str, now: datetime) -> tuple[SearchFilter, str]:
        if self.client:
            try:
                raw = self.client.generate_json(
                    f"Agora é {now.isoformat()}.\nPergunta: {question}", system=SYSTEM_FILTER)
                return SearchFilter.model_validate(raw), "gemini"
            except (GeminiError, ValidationError):
                pass
        return rule_based_filter(question, now), "regras"

    def summarize(self, question: str, f: SearchFilter, total: int, stats: dict) -> tuple[str, str]:
        fallback = deterministic_summary(question, f, total, stats)
        if not self.client:
            return fallback, "regras"
        data = {"pergunta": question, "filtro": describe_filter(f), "analises_encontradas": total,
                "total_no_banco": stats["total"], "por_rotulo": stats["por_rotulo"],
                "para_revisao": stats["para_revisao"], "limpezas_acionadas": stats["limpezas_acionadas"]}
        try:
            text = self.client.generate(json.dumps(data, ensure_ascii=False), system=SYSTEM_SUMMARY)
        except GeminiError:
            return fallback, "regras"
        if not text or not _numbers(text) <= _allowed_numbers(data):
            return fallback, "regras"                      # número inventado: descarta
        return text, "gemini"

    def explain(self, topic: str) -> tuple[str, str]:
        """Informação geral (ex.: 'o que é soiling?'). Sem dados do banco; sempre marcada como IA."""
        if not self.client:
            return ("A IA não está configurada (GEMINI_API_KEY e GEMINI_MODEL). Veja docs/06_ASSISTENTE_GEMINI.md.", "regras")
        try:
            text = self.client.generate(
                topic, system="Responda em português, em até 5 frases, sobre limpeza e sujidade (soiling) de painéis solares. "
                              "Se não souber, diga que não sabe. Não cite números de estudos.")
            return text, "gemini"
        except GeminiError:
            return "A IA está indisponível no momento.", "regras"
