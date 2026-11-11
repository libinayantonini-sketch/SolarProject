import os
from io import BytesIO

import pytest
from PIL import Image

from app.api.routes import create_app
from app.config import Settings
from app.database.repository import Repository
from app.services.assistant.service import Assistant
from app.services.esp32 import Esp32Client
from app.services.server_model import ServerModel
from app.services.storage import ImageStore
from esp32_simulator.classifier import Classifier
from esp32_simulator.server import Device, serve
from esp32_simulator.tiny_model import build_tiny_model

SIZE = 32
RED, GREEN, BLUE = (230, 10, 10), (10, 230, 10), (10, 10, 230)    # modelo de teste: R->LIMPO, G->MODERADO, B->SEVERO
KEY = {"X-API-Key": "segredo"}


def make_jpeg(color=(10, 200, 10), size=(SIZE, SIZE), noise_seed: int | None = None, fmt="JPEG") -> bytes:
    img = Image.new("RGB", size, color)
    if noise_seed is not None:                       # hashes/bytes diferentes para a mesma cor
        img.load()[noise_seed % size[0], noise_seed % size[1]] = (255 - color[0], 255 - color[1], 255 - color[2])
    buf = BytesIO()
    img.save(buf, fmt, quality=95) if fmt == "JPEG" else img.save(buf, fmt)
    return buf.getvalue()


def database_urls():
    urls = ["sqlite:///:memory:"]
    if os.environ.get("TEST_DATABASE_URL"):
        urls.append(os.environ["TEST_DATABASE_URL"])         # Postgres real, quando disponível
    return urls


@pytest.fixture(params=database_urls(), ids=lambda u: u.split(":")[0])
def repo(request):
    r = Repository(request.param)
    r.reset_schema()
    yield r
    r.dispose()


@pytest.fixture(scope="session")
def tiny_dir(tmp_path_factory):
    return str(build_tiny_model(tmp_path_factory.mktemp("model"), size=SIZE))


@pytest.fixture(scope="session")
def server_model(tiny_dir):
    """Modelo grande de teste: o mesmo ONNX sintético (R->LIMPO, G->MODERADO, B->SEVERO), carregado pelo caminho real."""
    return ServerModel.load(tiny_dir)


@pytest.fixture
def simulator(tiny_dir):
    """ESP32 simulado de verdade (servidor HTTP em thread), com cooldown longo para testar o bloqueio."""
    dev = Device(Classifier.load(tiny_dir), key="chave-esp", pump_ms=3000, cooldown_s=3600)
    srv = serve(dev, "127.0.0.1", 0)
    yield dev, f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture
def settings(tmp_path):
    return Settings(admin_api_key="segredo", max_upload_mb=1, input_size=SIZE, storage_dir=str(tmp_path / "img"),
                    esp32_key="chave-esp")


@pytest.fixture
def client(repo, simulator, settings, server_model):
    from fastapi.testclient import TestClient
    _, url = simulator
    app = create_app(settings, repo=repo, esp32=Esp32Client(url, "chave-esp"), assistant=Assistant(None),
                     store=ImageStore(settings.storage_dir), server_model=server_model)
    with TestClient(app) as c:
        c.store = app.state.store
        yield c


def post(c, data, name="f.jpg", headers=None, **form):
    return c.post("/api/analyze", files={"file": (name, data, "image/jpeg")}, data=form, headers=headers or {})
