"""Cliente mínimo da API REST do Gemini (generateContent). Sem SDK: uma dependência a menos.

Ainda NÃO testado contra o serviço real neste repositório (sem acesso à rede no ambiente de construção).
Os testes usam um cliente falso. Primeiro teste real: scripts/check_gemini.py.
"""
from __future__ import annotations

import json
import re

import httpx

BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiError(RuntimeError):
    pass


class GeminiClient:
    def __init__(self, api_key: str, model: str, timeout: float = 20.0, transport: httpx.BaseTransport | None = None) -> None:
        if not api_key or not model:
            raise GeminiError("GEMINI_API_KEY e GEMINI_MODEL são obrigatórios")
        self.model = model
        self._http = httpx.Client(timeout=timeout, transport=transport, headers={"x-goog-api-key": api_key})

    def generate(self, prompt: str, *, system: str | None = None, json_output: bool = False, temperature: float = 0.2) -> str:
        body: dict = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if json_output:
            body["generationConfig"]["responseMimeType"] = "application/json"
        try:
            r = self._http.post(f"{BASE}/{self.model}:generateContent", json=body)
        except httpx.HTTPError as exc:
            raise GeminiError(f"falha de rede: {type(exc).__name__}") from exc
        if r.status_code != 200:
            raise GeminiError(f"HTTP {r.status_code}: {r.text[:200]}")
        try:
            return "".join(p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"]).strip()
        except (KeyError, IndexError, ValueError) as exc:
            raise GeminiError("resposta sem texto (bloqueada ou vazia)") from exc

    def generate_json(self, prompt: str, *, system: str | None = None) -> dict:
        text = self.generate(prompt, system=system, json_output=True, temperature=0.0)
        text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
        try:
            obj = json.loads(text)
        except ValueError as exc:
            raise GeminiError("a IA não devolveu JSON válido") from exc
        if not isinstance(obj, dict):
            raise GeminiError("a IA devolveu JSON que não é objeto")
        return obj
