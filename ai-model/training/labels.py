"""Rótulos e mapeamento de classes do dataset. Mesma ordem de backend/app/labels.py: a ordem é a das saídas do modelo."""
LABELS = ("LIMPO", "MODERADO", "SEVERO")

# Dataset Roboflow "solar-panel-dust-and-soiling": Clean, Dusty, Soiled.
# ATENÇÃO: Clean=LIMPO, Dusty=MODERADO, Soiled=SEVERO é uma SUPOSIÇÃO da equipe. Confira olhando exemplos de cada
# classe (docs/02_DATASET_E_TREINO.md) e ajuste com --class-map "Dusty=SEVERO,...".
DEFAULT_CLASS_MAP = {
    "clean": "LIMPO", "limpo": "LIMPO",
    "dusty": "MODERADO", "moderado": "MODERADO", "moderate": "MODERADO",
    "soiled": "SEVERO", "severo": "SEVERO", "severe": "SEVERO",
}


def parse_class_map(text: str | None) -> dict[str, str]:
    out = dict(DEFAULT_CLASS_MAP)
    for part in filter(None, (p.strip() for p in (text or "").split(","))):
        src, _, dst = part.partition("=")
        if dst.strip().upper() not in LABELS:
            raise ValueError(f"destino inválido em --class-map: {part!r}; use {LABELS}")
        out[src.strip().lower()] = dst.strip().upper()
    return out


def to_label(name: str, class_map: dict[str, str]) -> str:
    key = name.strip().lower()
    if key not in class_map:
        raise ValueError(f"classe desconhecida: {name!r}. Conhecidas: {sorted(class_map)}. Use --class-map.")
    return class_map[key]
