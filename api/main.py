"""
RiskPredictor-RPA — Enterprise AI Risk Mitigation API
======================================================
FastAPI service with Explainable AI (SHAP), PostgreSQL persistence,
PDF reporting, and automated retraining capabilities.

Author: Martin Zapana Berrospi
"""

import json
import os
import subprocess
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, Field

from utils.email_sender import enviar_reporte_email
from utils.reporte_profesional import generar_reporte_pdf

load_dotenv()

# ---------------------------------------------------------------------------
# Directorios y Rutas
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODELS_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")
OPCIONES_JSON_PATH = os.path.join(DATA_DIR, "opciones_formulario.json")
METRICS_JSON_PATH = os.path.join(MODELS_DIR, "metrics.json")


def get_model_path(filename: str) -> str:
    return os.path.join(MODELS_DIR, filename)


# ---------------------------------------------------------------------------
# Carga de Modelos y Artefactos de ML
# ---------------------------------------------------------------------------
class ModelRegistry:
    def __init__(self):
        self.model = None
        self.sobrecosto_model = None
        self.retraso_model = None
        self.le_tipo = None
        self.le_metodologia = None
        self.le_complejidad = None
        self.le_experiencia = None
        self.mlb = None
        self.le_riesgo = None
        self.explainer = None
        self.feature_names = None
        self.feature_display_names = None
        self.load_all()

    def load_all(self):
        try:
            self.model = joblib.load(get_model_path("modelo_xgb_riesgo_general.pkl"))
            self.sobrecosto_model = joblib.load(get_model_path("modelo_xgb_sobrecosto.pkl"))
            self.retraso_model = joblib.load(get_model_path("modelo_xgb_retraso.pkl"))
            self.le_tipo = joblib.load(get_model_path("le_tipo_proyecto.pkl"))
            self.le_metodologia = joblib.load(get_model_path("le_metodologia.pkl"))
            self.le_complejidad = joblib.load(get_model_path("le_complejidad.pkl"))
            self.le_experiencia = joblib.load(get_model_path("le_experiencia.pkl"))
            self.mlb = joblib.load(get_model_path("mlb_tecnologias.pkl"))
            self.le_riesgo = joblib.load(get_model_path("le_riesgo_general.pkl"))

            if os.path.exists(get_model_path("shap_explainer.pkl")):
                self.explainer = joblib.load(get_model_path("shap_explainer.pkl"))
            if os.path.exists(get_model_path("feature_list.pkl")):
                self.feature_names = joblib.load(get_model_path("feature_list.pkl"))
            if os.path.exists(get_model_path("feature_display_names.pkl")):
                self.feature_display_names = joblib.load(get_model_path("feature_display_names.pkl"))
            print("[ModelRegistry] Modelos y artefactos ML cargados exitosamente.")
        except Exception as e:
            print(f"[ModelRegistry] Error cargando artefactos ML: {e}")


registry = ModelRegistry()

# ---------------------------------------------------------------------------
# Base de Datos PostgreSQL
# ---------------------------------------------------------------------------
DB_URL = os.getenv("DATABASE_URL")


def get_db_connection():
    if not DB_URL:
        return None
    url = DB_URL
    if "sslmode=" not in url:
        url += "?sslmode=require" if "?" not in url else "&sslmode=require"
    return psycopg2.connect(url)


def init_db():
    if not DB_URL:
        print("[Database] DATABASE_URL no está configurada. Modo offline/fallback.")
        return
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS auditoria_predicciones (
                        id SERIAL PRIMARY KEY,
                        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        tipo_proyecto TEXT,
                        metodologia TEXT,
                        duracion_estimacion REAL,
                        presupuesto_estimado REAL,
                        numero_recursos REAL,
                        tecnologias TEXT,
                        complejidad TEXT,
                        experiencia_equipo REAL,
                        hitos_clave REAL,
                        riesgo_general TEXT,
                        probabilidad_sobrecosto REAL,
                        probabilidad_retraso REAL,
                        explicabilidad_top JSONB
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS proyectos_ejecucion (
                        id TEXT PRIMARY KEY,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        tipo_proyecto TEXT,
                        metodologia TEXT,
                        duracion_estimacion REAL,
                        presupuesto_estimado REAL,
                        numero_recursos REAL,
                        tecnologias TEXT,
                        complejidad TEXT,
                        experiencia_equipo REAL,
                        hitos_clave REAL,
                        costo_real REAL,
                        duracion_real REAL,
                        riesgo_general TEXT,
                        estado TEXT DEFAULT 'ejecucion'
                    );
                """)
                conn.commit()
        print("[Database] Tablas PostgreSQL inicializadas correctamente.")
    except Exception as e:
        print(f"[Database] Error inicializando base de datos Postgres: {e}")


def _save_audit_log(proyecto_dict: dict, prediction_result: dict):
    if not DB_URL:
        return
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO auditoria_predicciones (
                        tipo_proyecto, metodologia, duracion_estimacion, presupuesto_estimado, 
                        numero_recursos, tecnologias, complejidad, experiencia_equipo, hitos_clave,
                        riesgo_general, probabilidad_sobrecosto, probabilidad_retraso, explicabilidad_top
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    proyecto_dict.get("tipo_proyecto"),
                    proyecto_dict.get("metodologia"),
                    proyecto_dict.get("duracion_estimacion"),
                    proyecto_dict.get("presupuesto_estimado"),
                    proyecto_dict.get("numero_recursos"),
                    proyecto_dict.get("tecnologias"),
                    proyecto_dict.get("complejidad"),
                    proyecto_dict.get("experiencia_equipo"),
                    proyecto_dict.get("hitos_clave"),
                    prediction_result.get("riesgo_general"),
                    prediction_result.get("probabilidad_sobrecosto", 0),
                    prediction_result.get("probabilidad_retraso", 0),
                    json.dumps(prediction_result.get("factores_explicabilidad", []))
                ))
                conn.commit()
    except Exception as e:
        print(f"[Database] Error guardando log de auditoría: {e}")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="RiskPredictor-RPA Analytics Engine",
    description="Enterprise Machine Learning platform for predictive project risk assessment and Explainable AI (SHAP).",
    version="2.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Modelos Pydantic (Schemas)
# ---------------------------------------------------------------------------
class ProyectoInput(BaseModel):
    tipo_proyecto: str = Field(..., description="Tipo de proyecto TI", json_schema_extra={"example": "implementación ERP"})
    metodologia: str = Field(..., description="Metodología de gestión", json_schema_extra={"example": "agile"})
    duracion_estimacion: float = Field(..., gt=0, description="Duración estimada en meses", json_schema_extra={"example": 12.0})
    presupuesto_estimado: float = Field(..., gt=0, description="Presupuesto estimado en USD", json_schema_extra={"example": 500000.0})
    numero_recursos: float = Field(..., gt=0, description="Cantidad de recursos asignados", json_schema_extra={"example": 8.0})
    tecnologias: str = Field(..., description="Tecnologías separadas por coma", json_schema_extra={"example": "cloud,IA"})
    complejidad: str = Field(..., description="Nivel de complejidad", json_schema_extra={"example": "alta"})
    experiencia_equipo: float = Field(..., ge=0, description="Experiencia promedio del equipo (años)", json_schema_extra={"example": 5.0})
    hitos_clave: float = Field(..., ge=1, description="Número de hitos clave planificados", json_schema_extra={"example": 6.0})


class FactorExplicabilidad(BaseModel):
    factor: str
    impacto_shap: float
    direccion: str
    descripcion: str


class PredictionResponse(BaseModel):
    riesgo_general: str
    probabilidades_riesgo: Dict[str, float]
    probabilidad_sobrecosto: float
    probabilidad_retraso: float
    factores_explicabilidad: List[FactorExplicabilidad]


class EnvioReporteRequest(BaseModel):
    destinatario: str
    proyecto: dict
    prediccion: Optional[dict] = None


class ProyectoUpdate(BaseModel):
    tipo_proyecto: Optional[str] = None
    metodologia: Optional[str] = None
    duracion_estimacion: Optional[float] = None
    presupuesto_estimado: Optional[float] = None
    numero_recursos: Optional[float] = None
    tecnologias: Optional[str] = None
    complejidad: Optional[str] = None
    experiencia_equipo: Optional[float] = None
    hitos_clave: Optional[float] = None
    costo_real: Optional[float] = None
    duracion_real: Optional[float] = None
    riesgo_general: Optional[str] = None
    estado: Optional[str] = None


# ---------------------------------------------------------------------------
# Motor de Inferencia y XAI (SHAP)
# ---------------------------------------------------------------------------
def _preprocess_features(proyecto_dict: dict) -> pd.DataFrame:
    """Transforma un diccionario de entrada en el vector de features listo para XGBoost."""
    X_pred = pd.DataFrame([proyecto_dict])
    
    try:
        X_pred["tipo_proyecto_enc"] = registry.le_tipo.transform(X_pred["tipo_proyecto"])
    except Exception:
        X_pred["tipo_proyecto_enc"] = 0
        
    try:
        X_pred["metodologia_enc"] = registry.le_metodologia.transform(X_pred["metodologia"])
    except Exception:
        X_pred["metodologia_enc"] = 0
        
    try:
        X_pred["complejidad_enc"] = registry.le_complejidad.transform(X_pred["complejidad"])
    except Exception:
        X_pred["complejidad_enc"] = 0
        
    X_pred["experiencia_equipo_enc"] = float(X_pred["experiencia_equipo"].values[0])

    # Tecnologías Multi-Hot
    tec_str = str(proyecto_dict.get("tecnologias", ""))
    tec_list = [t.strip() for t in tec_str.split(",") if t.strip()]
    tec_matrix = registry.mlb.transform([tec_list])
    tec_df = pd.DataFrame(tec_matrix, columns=[f"tec_{t}" for t in registry.mlb.classes_])
    for col in tec_df.columns:
        X_pred[col] = tec_df[col].values

    # Features requeridos
    features = registry.feature_names or [
        "tipo_proyecto_enc", "metodologia_enc", "duracion_estimacion", "presupuesto_estimado",
        "numero_recursos", "complejidad_enc", "experiencia_equipo_enc", "hitos_clave"
    ] + list(tec_df.columns)

    for col in features:
        if col not in X_pred.columns:
            X_pred[col] = 0

    return X_pred[features]


def _compute_shap_explanations(X_pred: pd.DataFrame, predicted_class_idx: int) -> List[Dict[str, Any]]:
    """Calcula los factores determinantes locales con SHAP."""
    if registry.explainer is None:
        return []
    try:
        shap_vals = registry.explainer.shap_values(X_pred)
        shap_arr = np.array(shap_vals)

        # Extraer vector 1D de SHAP para la clase predicha
        if shap_arr.ndim == 3:
            if shap_arr.shape[0] == len(registry.le_riesgo.classes_):
                vals = shap_arr[predicted_class_idx, 0, :]
            else:
                vals = shap_arr[0, :, predicted_class_idx]
        elif shap_arr.ndim == 2:
            vals = shap_arr[0, :]
        else:
            vals = np.ravel(shap_arr)

        features = list(X_pred.columns)
        display_map = registry.feature_display_names or {}

        # Ordenar por magnitud de impacto absoluto |SHAP|
        indices = np.argsort(np.abs(vals))[::-1][:5]
        factores = []
        for idx in indices:
            feat_name = features[idx]
            impact = float(vals[idx])
            display_name = display_map.get(feat_name, feat_name.replace("_enc", "").replace("_", " ").title())
            
            direccion = "incrementa_riesgo" if impact > 0 else "reduce_riesgo"
            desc = (
                f"Eleva la probabilidad de riesgo ({impact:+.2f})"
                if impact > 0
                else f"Atenúa y estabiliza el riesgo ({impact:+.2f})"
            )
            factores.append({
                "factor": display_name,
                "impacto_shap": round(impact, 4),
                "direccion": direccion,
                "descripcion": desc,
            })
        return factores
    except Exception as e:
        print(f"[SHAP] Error computando explicabilidad: {e}")
        return []


def _predict_risk(proyecto_dict: dict) -> dict:
    """Ejecuta inferencia multi-objetivo y genera explicabilidad."""
    X_pred = _preprocess_features(proyecto_dict)

    pred_idx = registry.model.predict(X_pred)[0]
    pred_label = registry.le_riesgo.inverse_transform([pred_idx])[0]
    pred_proba = registry.model.predict_proba(X_pred)[0]

    sobrecosto_proba = float(registry.sobrecosto_model.predict_proba(X_pred)[0][1])
    retraso_proba = float(registry.retraso_model.predict_proba(X_pred)[0][1])

    factores = _compute_shap_explanations(X_pred, int(pred_idx))

    return {
        "riesgo_general": pred_label,
        "probabilidades_riesgo": {
            clase: float(proba)
            for clase, proba in zip(registry.le_riesgo.classes_, pred_proba)
        },
        "probabilidad_sobrecosto": sobrecosto_proba,
        "probabilidad_retraso": retraso_proba,
        "factores_explicabilidad": factores,
    }


def _proyecto_to_display_dict(proyecto_dict: dict) -> dict:
    return {
        "Tipo de proyecto": proyecto_dict.get("tipo_proyecto", ""),
        "Metodología": proyecto_dict.get("metodologia", ""),
        "Duración estimada (meses)": proyecto_dict.get("duracion_estimacion", ""),
        "Presupuesto estimado (USD)": proyecto_dict.get("presupuesto_estimado", ""),
        "Número de recursos": proyecto_dict.get("numero_recursos", ""),
        "Tecnologías": proyecto_dict.get("tecnologias", ""),
        "Complejidad": proyecto_dict.get("complejidad", ""),
        "Experiencia del equipo": proyecto_dict.get("experiencia_equipo", ""),
        "Hitos clave": proyecto_dict.get("hitos_clave", ""),
    }


def _prediccion_to_report_dict(prediccion: dict) -> dict:
    return {
        "riesgo_general": prediccion.get("riesgo_general", ""),
        "probabilidades": prediccion.get("probabilidades_riesgo") or prediccion.get("probabilidades", {}),
        "probabilidad_sobrecosto": prediccion.get("probabilidad_sobrecosto", 0),
        "probabilidad_retraso": prediccion.get("probabilidad_retraso", 0),
        "factores_explicabilidad": prediccion.get("factores_explicabilidad", []),
    }


# ---------------------------------------------------------------------------
# Endpoints de la API
# ---------------------------------------------------------------------------

@app.get("/", tags=["Sistema"])
def root():
    return {
        "sistema": "RiskPredictor-RPA Analytics API",
        "version": "2.0.0",
        "status": "online",
        "docs": "/docs",
    }


@app.get("/health", tags=["Sistema"])
def health_check():
    models_ok = registry.model is not None and registry.explainer is not None
    db_ok = False
    if DB_URL:
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    db_ok = True
        except Exception:
            db_ok = False
    return {
        "status": "healthy" if models_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "models_loaded": models_ok,
        "database_connected": db_ok,
    }


@app.get("/metricas", tags=["Machine Learning"])
def get_model_metrics():
    """Devuelve las métricas de rendimiento y validación del modelo."""
    if os.path.exists(METRICS_JSON_PATH):
        with open(METRICS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"message": "Métricas no disponibles. Ejecute el script de entrenamiento."}


@app.post("/predict", response_model=PredictionResponse, tags=["Inferencia"])
def predict_riesgo(proyecto: ProyectoInput):
    """Ejecuta inferencia multi-objetivo y calcula explicabilidad con SHAP."""
    data = proyecto.model_dump()
    resultado = _predict_risk(data)
    _save_audit_log(data, resultado)
    return resultado


@app.get("/opciones-formulario", tags=["Configuración"])
def get_opciones_formulario():
    if os.path.exists(OPCIONES_JSON_PATH):
        with open(OPCIONES_JSON_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content=data)
    return JSONResponse(content={
        "tipo_proyecto": ["desarrollo software", "migración", "implementación ERP", "integración sistemas", "automatización RPA", "modernización", "soporte TI"],
        "tecnologias": ["cloud", "big data", "IA", "IoT", "blockchain", "mobile", "web"],
        "metodologia": ["agile", "scrum", "kanban", "cascada"]
    })


@app.put("/opciones-formulario", tags=["Configuración"])
def update_opciones_formulario(new_data: dict):
    with open(OPCIONES_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Gestión de Proyectos en Ejecución (CRUD PostgreSQL)
# ---------------------------------------------------------------------------

@app.post("/proyectos-ejecucion", tags=["Proyectos"])
def add_proyecto_ejecucion(proyecto: dict):
    proyecto_id = str(uuid.uuid4())
    if not DB_URL:
        return {"status": "ok", "id": proyecto_id}
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO proyectos_ejecucion (
                        id, tipo_proyecto, metodologia, duracion_estimacion, presupuesto_estimado,
                        numero_recursos, tecnologias, complejidad, experiencia_equipo, hitos_clave
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    proyecto_id,
                    proyecto.get("tipo_proyecto"),
                    proyecto.get("metodologia"),
                    proyecto.get("duracion_estimacion"),
                    proyecto.get("presupuesto_estimado"),
                    proyecto.get("numero_recursos"),
                    proyecto.get("tecnologias"),
                    proyecto.get("complejidad"),
                    proyecto.get("experiencia_equipo"),
                    proyecto.get("hitos_clave"),
                ))
                conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    return {"status": "ok", "id": proyecto_id}


@app.get("/proyectos-ejecucion", tags=["Proyectos"])
def list_proyectos_ejecucion():
    if not DB_URL:
        return []
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM proyectos_ejecucion ORDER BY fecha_creacion DESC")
                rows = cursor.fetchall()
                for r in rows:
                    if "fecha_creacion" in r and r["fecha_creacion"]:
                        r["fecha_creacion"] = r["fecha_creacion"].isoformat()
                return [dict(row) for row in rows]
    except Exception as e:
        print(f"[Proyectos] Error listando proyectos: {e}")
        return []


@app.get("/proyectos-ejecucion/{proy_id}", tags=["Proyectos"])
def get_proyecto_ejecucion(proy_id: str):
    if not DB_URL:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM proyectos_ejecucion WHERE id = %s", (proy_id,))
                row = cursor.fetchone()
                if row:
                    if "fecha_creacion" in row and row["fecha_creacion"]:
                        row["fecha_creacion"] = row["fecha_creacion"].isoformat()
                    return dict(row)
    except Exception:
        pass
    raise HTTPException(status_code=404, detail="Proyecto no encontrado")


@app.put("/proyectos-ejecucion/{proy_id}", tags=["Proyectos"])
def update_proyecto_ejecucion(proy_id: str, datos: dict):
    if not DB_URL:
        return {"status": "ok"}
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                valid_keys = [k for k in datos.keys() if k != "id"]
                if not valid_keys:
                    return {"status": "ok"}
                set_clause = ", ".join([f"{k} = %s" for k in valid_keys])
                values = [datos[k] for k in valid_keys]
                values.append(proy_id)
                cursor.execute(f"UPDATE proyectos_ejecucion SET {set_clause} WHERE id = %s", values)
                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Proyecto no encontrado")
                conn.commit()
                return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/proyectos-ejecucion/{proy_id}", tags=["Proyectos"])
def delete_proyecto_ejecucion(proy_id: str):
    """Elimina un proyecto de la base de datos PostgreSQL de forma segura."""
    if not DB_URL:
        return {"status": "ok"}
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM proyectos_ejecucion WHERE id = %s", (proy_id,))
                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Proyecto no encontrado")
                conn.commit()
                return {"status": "ok", "message": f"Proyecto {proy_id} eliminado exitosamente."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/proyectos-ejecucion/{proy_id}/finalizar", tags=["Proyectos"])
def finalizar_proyecto(proy_id: str, datos_finales: dict):
    if not DB_URL:
        return {"status": "ok"}
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM proyectos_ejecucion WHERE id = %s", (proy_id,))
                proyecto = cursor.fetchone()
                if not proyecto:
                    raise HTTPException(status_code=404, detail="Proyecto no encontrado")

                cursor.execute("""
                    UPDATE proyectos_ejecucion 
                    SET costo_real = %s, duracion_real = %s, riesgo_general = %s, estado = 'finalizado'
                    WHERE id = %s
                """, (
                    datos_finales.get("costo_real"),
                    datos_finales.get("duracion_real"),
                    datos_finales.get("riesgo_general", proyecto.get("riesgo_general")),
                    proy_id,
                ))
                conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error en base de datos al finalizar")

    # Retroalimentación a CSVs para reentrenamiento continuo
    try:
        finalizado = {**dict(proyecto), **datos_finales}
        dataset_path = os.path.join(DATA_DIR, "dataset.csv")
        synth_fields = [
            "tipo_proyecto", "metodologia", "duracion_estimacion", "presupuesto_estimado",
            "numero_recursos", "tecnologias", "complejidad", "experiencia_equipo", "hitos_clave",
            "costo_real", "duracion_real", "riesgo_general"
        ]
        import csv
        with open(dataset_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=synth_fields, extrasaction="ignore")
            writer.writerow(finalizado)
    except Exception as e:
        print(f"[Feedback Loop] Error guardando registro finalizado en dataset: {e}")

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Reentrenamiento de Modelos
# ---------------------------------------------------------------------------

@app.post("/reentrenar-modelo", tags=["Machine Learning"])
def reentrenar_modelo(background_tasks: BackgroundTasks):
    """Ejecuta el pipeline de reentrenamiento y recarga los modelos en memoria."""
    script_path = os.path.join(MODELS_DIR, "train_xgboost.py")
    python_exe = sys.executable
    try:
        result = subprocess.run(
            [python_exe, script_path],
            capture_output=True,
            text=True,
            check=True,
            cwd=BASE_DIR,
        )
        registry.load_all()
        return {"status": "ok", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "output": e.stdout + "\n" + e.stderr}


# ---------------------------------------------------------------------------
# Generación y Envío de Reportes PDF
# ---------------------------------------------------------------------------

@app.post("/generar-reporte", tags=["Reportes"])
def generar_reporte(proyecto: ProyectoInput):
    data = proyecto.model_dump()
    prediccion = _predict_risk(data)
    proyecto_dict = _proyecto_to_display_dict(data)
    prediccion_dict = _prediccion_to_report_dict(prediccion)
    pdf_path = os.path.join(BASE_DIR, f"reporte_riesgo_{uuid.uuid4().hex}.pdf")
    generar_reporte_pdf(proyecto_dict, prediccion_dict, filename=pdf_path)
    return FileResponse(pdf_path, media_type="application/pdf", filename="reporte_riesgo_ejecutivo.pdf")


@app.post("/enviar-reporte-mailhog", tags=["Reportes"])
def enviar_reporte_email_endpoint(request: EnvioReporteRequest):
    """Genera el reporte PDF ejecutivo y lo despacha por email SMTP."""
    prediccion = request.prediccion
    if not prediccion or not prediccion.get("probabilidades_riesgo") and not prediccion.get("probabilidades"):
        if request.proyecto:
            prediccion = _predict_risk(request.proyecto)

    proyecto_dict = _proyecto_to_display_dict(request.proyecto)
    prediccion_dict = _prediccion_to_report_dict(prediccion or {})
    pdf_path = os.path.join(BASE_DIR, f"reporte_riesgo_{uuid.uuid4().hex}.pdf")
    generar_reporte_pdf(proyecto_dict, prediccion_dict, filename=pdf_path)

    asunto = "Reporte Ejecutivo de Evaluación de Riesgo — RiskPredictor RPA"
    cuerpo = (
        "Estimado/a,\n\n"
        "Adjunto encontrará el informe de evaluación y mitigación de riesgos generado por el "
        "motor predictivo de Inteligencia Artificial (XGBoost + SHAP Explainability).\n\n"
        "RiskPredictor RPA — Enterprise Analytics"
    )
    try:
        enviar_reporte_email(request.destinatario, asunto, cuerpo, pdf_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception:
            pass
    return {"mensaje": "Reporte enviado correctamente al email de destino."}
