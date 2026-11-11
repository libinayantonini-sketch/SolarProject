"""Configuração por variáveis de ambiente (ver .env.example). Nenhum segredo no código."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from app.labels import parse_classes


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./data/app.db"
    storage_dir: str = "./storage/images"       # imagens ficam em arquivos; o banco guarda só o caminho relativo
    esp32_url: str = ""                          # ex.: http://192.168.0.50 (vazio = ESP32 não configurado)
    esp32_key: str = ""                          # segredo compartilhado opcional (cabeçalho X-Device-Key)
    esp32_timeout_s: float = 30.0
    input_size: int = 96                         # lado da imagem do modelo do ESP32 (ESP32_INPUT_SIZE; igual ao do treino/firmware)
    esp32_classes: tuple[str, ...] = ("LIMPO", "MODERADO", "SEVERO")   # ESP32_CLASSES; use "LIMPO,SEVERO" se o modelo do ESP32 tiver 2 classes
    jpeg_quality: int = 85
    low_confidence_threshold: float = 0.60
    admin_api_key: str = ""                      # vazio = sem proteção (só desenvolvimento local)
    gemini_api_key: str = ""
    gemini_model: str = ""                       # sem padrão de propósito: nomes de modelo mudam; defina no .env
    max_upload_mb: int = 10
    cors_origins: tuple[str, ...] = field(default_factory=tuple)
    server_model_dir: str = "models/server"     # pasta do modelo grande (ONNX), opcional; veja docs/12_MODELO_NO_SERVIDOR.md
    server_input_size: int = 0                   # SERVER_INPUT_SIZE: lado da entrada do modelo grande; 0 = usar o model_card.json
    upload_max_side: int = 512                   # o front reduz a foto para no máximo isto; o backend gera o tamanho de cada modelo
    weather_enabled: bool = True                 # recomendação de chuva (Open-Meteo); só informa, nunca aciona a bomba
    panel_lat: float = -23.3103                  # Londrina-PR (provisório: troque pela posição real do painel)
    panel_lon: float = -51.1628
    rain_light_mm: float = 1.0                   # PROVISÓRIO: a partir daqui a chuva prevista em 24 h já "conta" (fraca)
    rain_heavy_mm: float = 10.0                  # PROVISÓRIO: a partir daqui a chuva prevista em 24 h é forte
    frontend_dir: str = ""                       # pasta do build do front (frontend/dist); vazio = não serve front

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_model)

    @classmethod
    def from_env(cls) -> "Settings":
        e = os.environ
        default_front = Path(__file__).resolve().parents[2] / "frontend" / "dist"
        return cls(
            database_url=e.get("DATABASE_URL", cls.database_url),
            storage_dir=e.get("STORAGE_DIR", cls.storage_dir),
            esp32_url=e.get("ESP32_URL", "").rstrip("/"),
            esp32_key=e.get("ESP32_KEY", ""),
            esp32_timeout_s=float(e.get("ESP32_TIMEOUT_S", "30")),
            input_size=int(e.get("ESP32_INPUT_SIZE", e.get("INPUT_SIZE", "96"))),     # INPUT_SIZE = nome antigo, ainda aceito
            esp32_classes=tuple(l.value for l in parse_classes(e.get("ESP32_CLASSES", "LIMPO,MODERADO,SEVERO"))),
            jpeg_quality=int(e.get("JPEG_QUALITY", "85")),
            low_confidence_threshold=float(e.get("LOW_CONFIDENCE_THRESHOLD", "0.60")),
            admin_api_key=e.get("ADMIN_API_KEY", ""),
            gemini_api_key=e.get("GEMINI_API_KEY", ""),
            gemini_model=e.get("GEMINI_MODEL", ""),
            max_upload_mb=int(e.get("MAX_UPLOAD_MB", "10")),
            cors_origins=tuple(o.strip() for o in e.get("CORS_ORIGINS", "").split(",") if o.strip()),
            server_model_dir=e.get("SERVER_MODEL_DIR", "models/server"),
            server_input_size=int(e.get("SERVER_INPUT_SIZE", "0")),
            upload_max_side=int(e.get("UPLOAD_MAX_SIDE", "512")),
            weather_enabled=e.get("WEATHER_ENABLED", "1").strip().lower() in {"1", "true", "yes", "sim"},
            panel_lat=float(e.get("PANEL_LAT", "-23.3103")),
            panel_lon=float(e.get("PANEL_LON", "-51.1628")),
            rain_light_mm=float(e.get("RAIN_LIGHT_MM", "1.0")),
            rain_heavy_mm=float(e.get("RAIN_HEAVY_MM", "10.0")),
            frontend_dir=e.get("FRONTEND_DIR", str(default_front) if default_front.is_dir() else ""),
        )
