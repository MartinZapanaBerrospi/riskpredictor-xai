import pytest
import os
import sys
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "RiskPredictor" in data["sistema"]
    assert data["version"] == "2.0.0"


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "models_loaded" in data
    assert data["models_loaded"] is True


def test_metricas_endpoint():
    response = client.get("/metricas")
    assert response.status_code == 200
    data = response.json()
    assert "riesgo_general" in data or "dataset" in data


def test_opciones_formulario_endpoint():
    response = client.get("/opciones-formulario")
    assert response.status_code == 200
    data = response.json()
    assert "tipo_proyecto" in data
    assert "tecnologias" in data


def test_predict_endpoint_valid():
    payload = {
        "tipo_proyecto": "desarrollo software",
        "metodologia": "scrum",
        "duracion_estimacion": 12,
        "presupuesto_estimado": 400000,
        "numero_recursos": 8,
        "tecnologias": "cloud,web",
        "complejidad": "media",
        "experiencia_equipo": 6,
        "hitos_clave": 4
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["riesgo_general"] in ["Alto", "Medio", "Bajo"]
    assert "probabilidades_riesgo" in data
    assert "factores_explicabilidad" in data
    assert len(data["factores_explicabilidad"]) > 0


def test_predict_endpoint_invalid_payload():
    payload = {
        "tipo_proyecto": "desarrollo software"
        # Missing required fields
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 422
