import pytest
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main import _predict_risk, registry, _preprocess_features


@pytest.fixture(scope="module")
def sample_project():
    return {
        "tipo_proyecto": "implementación ERP",
        "metodologia": "agile",
        "duracion_estimacion": 18.0,
        "presupuesto_estimado": 850000.0,
        "numero_recursos": 14.0,
        "tecnologias": "cloud,IA,big data",
        "complejidad": "alta",
        "experiencia_equipo": 4.0,
        "hitos_clave": 6.0,
    }


def test_models_loaded():
    assert registry.model is not None, "El modelo multiclase principal debe estar cargado"
    assert registry.sobrecosto_model is not None, "El modelo de sobrecosto debe estar cargado"
    assert registry.retraso_model is not None, "El modelo de retraso debe estar cargado"
    assert registry.explainer is not None, "El explainer SHAP debe estar cargado"


def test_preprocess_features(sample_project):
    X = _preprocess_features(sample_project)
    assert len(X) == 1, "Debe generar una fila"
    assert "tipo_proyecto_enc" in X.columns
    assert "duracion_estimacion" in X.columns


def test_predict_risk_structure(sample_project):
    result = _predict_risk(sample_project)

    assert "riesgo_general" in result
    assert result["riesgo_general"] in ["Alto", "Medio", "Bajo"]

    assert "probabilidades_riesgo" in result
    probs = result["probabilidades_riesgo"]
    assert len(probs) == 3
    assert abs(sum(probs.values()) - 1.0) < 0.01

    assert "probabilidad_sobrecosto" in result
    assert 0.0 <= result["probabilidad_sobrecosto"] <= 1.0

    assert "probabilidad_retraso" in result
    assert 0.0 <= result["probabilidad_retraso"] <= 1.0

    assert "factores_explicabilidad" in result
    factores = result["factores_explicabilidad"]
    assert isinstance(factores, list)
    assert len(factores) > 0

    first_factor = factores[0]
    assert "factor" in first_factor
    assert "impacto_shap" in first_factor
    assert "direccion" in first_factor
    assert first_factor["direccion"] in ["incrementa_riesgo", "reduce_riesgo"]
