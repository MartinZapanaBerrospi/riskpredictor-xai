"""
RiskPredictor — Pipeline de entrenamiento de modelos XGBoost
================================================================
Entrena 3 modelos supervisados para predicción de riesgos en proyectos TI:
  1. Riesgo General (multiclase: Alto / Medio / Bajo)
  2. Probabilidad de Sobrecosto (binario)
  3. Probabilidad de Retraso (binario)

Metodología:
  - Stratified Train/Test Split ANTES del balanceo (evita data leakage)
  - Upsampling solo en el conjunto de entrenamiento
  - GridSearchCV con Stratified K-Fold para optimización de hiperparámetros
  - SHAP TreeExplainer para explicabilidad del modelo
  - Exportación de métricas y artefactos de evaluación

Autor: Martin Zapana Berrospi
"""

import json
import os
import warnings

import joblib
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.preprocessing import LabelEncoder, MultiLabelBinarizer
from sklearn.utils import resample

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
MODELS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.abspath(os.path.join(MODELS_DIR, "..", "data", "dataset.csv"))
METRICS_PATH = os.path.join(MODELS_DIR, "metrics.json")


def model_path(filename: str) -> str:
    return os.path.join(MODELS_DIR, filename)


# ---------------------------------------------------------------------------
# 1. Carga y preprocesamiento
# ---------------------------------------------------------------------------
print("=" * 60)
print("FASE 1: Carga de datos y preprocesamiento")
print("=" * 60)

df = pd.read_csv(DATA_PATH)
print(f"Dataset cargado: {len(df)} registros, {len(df.columns)} columnas")

# Codificación de variables categóricas
le_tipo = LabelEncoder()
df["tipo_proyecto_enc"] = le_tipo.fit_transform(df["tipo_proyecto"])

le_metodologia = LabelEncoder()
df["metodologia_enc"] = le_metodologia.fit_transform(df["metodologia"])

le_complejidad = LabelEncoder()
df["complejidad_enc"] = le_complejidad.fit_transform(df["complejidad"])

le_experiencia = LabelEncoder()
df["experiencia_equipo_enc"] = le_experiencia.fit_transform(df["experiencia_equipo"])

# Tecnologías: multi-hot encoding
mlb = MultiLabelBinarizer()
tec_matrix = mlb.fit_transform(df["tecnologias"].astype(str).str.split(","))
tec_df = pd.DataFrame(tec_matrix, columns=[f"tec_{t}" for t in mlb.classes_])
df = pd.concat([df, tec_df], axis=1)

# Features finales
FEATURES = [
    "tipo_proyecto_enc",
    "metodologia_enc",
    "duracion_estimacion",
    "presupuesto_estimado",
    "numero_recursos",
    "complejidad_enc",
    "experiencia_equipo_enc",
    "hitos_clave",
] + list(tec_df.columns)

# Targets
le_riesgo = LabelEncoder()
df["riesgo_general_enc"] = le_riesgo.fit_transform(df["riesgo_general"])
df["sobrecosto"] = (df["costo_real"] > df["presupuesto_estimado"]).astype(int)
df["retraso"] = (df["duracion_real"] > df["duracion_estimacion"]).astype(int)

print(f"Features: {len(FEATURES)}")
print(f"Clases de riesgo: {list(le_riesgo.classes_)}")
print(f"Distribución original: {dict(df['riesgo_general'].value_counts())}")


# ---------------------------------------------------------------------------
# 2. Split estratificado ANTES del balanceo (elimina data leakage)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("FASE 2: Split estratificado (data leakage-free)")
print("=" * 60)

X = df[FEATURES]
y_riesgo = df["riesgo_general_enc"]
y_sobrecosto = df["sobrecosto"]
y_retraso = df["retraso"]

# Split principal: 80% train, 20% test — ESTRATIFICADO por la variable target
X_train, X_test, y_train, y_test = train_test_split(
    X, y_riesgo, test_size=0.2, random_state=42, stratify=y_riesgo
)

# Alinear los targets binarios con los mismos índices
y_train_sobrecosto = y_sobrecosto.loc[X_train.index]
y_test_sobrecosto = y_sobrecosto.loc[X_test.index]
y_train_retraso = y_retraso.loc[X_train.index]
y_test_retraso = y_retraso.loc[X_test.index]

print(f"Train: {len(X_train)} registros | Test: {len(X_test)} registros")
print(f"Distribución en train: {dict(pd.Series(y_train).value_counts())}")
print(f"Distribución en test:  {dict(pd.Series(y_test).value_counts())}")


# ---------------------------------------------------------------------------
# 3. Balanceo SOLO del training set (upsampling de clases minoritarias)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("FASE 3: Balanceo del training set (sin contaminar test)")
print("=" * 60)


def balance_training_set(X_tr, y_tr):
    """Aplica upsampling SOLO al conjunto de entrenamiento."""
    train_df = X_tr.copy()
    train_df["__target__"] = y_tr.values

    classes = train_df["__target__"].unique()
    class_dfs = [train_df[train_df["__target__"] == c] for c in classes]
    max_count = max(len(d) for d in class_dfs)

    balanced = pd.concat(
        [
            resample(d, replace=True, n_samples=max_count, random_state=42)
            if len(d) < max_count
            else d
            for d in class_dfs
        ]
    )

    y_balanced = balanced.pop("__target__")
    return balanced, y_balanced


X_train_bal, y_train_bal = balance_training_set(X_train, y_train)
print(f"Train balanceado: {len(X_train_bal)} registros")
print(f"Distribución balanceada: {dict(pd.Series(y_train_bal).value_counts())}")


# ---------------------------------------------------------------------------
# 4. Entrenamiento del modelo de Riesgo General (XGBoost multiclase)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("FASE 4: Entrenamiento XGBoost — Riesgo General (multiclase)")
print("=" * 60)

param_grid = {
    "n_estimators": [100, 200],
    "max_depth": [4, 6, 8],
    "learning_rate": [0.05, 0.1, 0.2],
    "subsample": [0.8, 1.0],
    "colsample_bytree": [0.8, 1.0],
}

xgb_base = xgb.XGBClassifier(
    objective="multi:softprob",
    num_class=len(le_riesgo.classes_),
    eval_metric="mlogloss",
    random_state=42,
)

cv_strategy = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

grid_search = GridSearchCV(
    xgb_base,
    param_grid,
    cv=cv_strategy,
    scoring="f1_weighted",
    n_jobs=-1,
    verbose=1,
)
grid_search.fit(X_train_bal, y_train_bal)

print(f"\nMejores hiperparámetros: {grid_search.best_params_}")
print(f"Mejor F1-weighted (CV): {grid_search.best_score_:.4f}")

model = grid_search.best_estimator_

# Evaluación en test set LIMPIO (nunca visto, nunca balanceado)
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)

print("\n--- Evaluación en Test Set (datos reales, no balanceados) ---")
report = classification_report(
    y_test, y_pred, target_names=le_riesgo.classes_, output_dict=True
)
print(classification_report(y_test, y_pred, target_names=le_riesgo.classes_))
print("Matriz de confusión:")
cm = confusion_matrix(y_test, y_pred)
print(cm)

roc_auc = roc_auc_score(y_test, y_proba, multi_class="ovr")
logloss = log_loss(y_test, y_proba)
f1_w = f1_score(y_test, y_pred, average="weighted")
print(f"ROC-AUC (OvR): {roc_auc:.4f}")
print(f"Log-loss: {logloss:.4f}")
print(f"F1-Score (weighted): {f1_w:.4f}")


# ---------------------------------------------------------------------------
# 5. Entrenamiento modelo Sobrecosto (XGBoost binario)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("FASE 5: Entrenamiento XGBoost — Probabilidad de Sobrecosto")
print("=" * 60)

sobrecosto_model = xgb.XGBClassifier(
    objective="binary:logistic",
    eval_metric="logloss",
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    random_state=42,
)
sobrecosto_model.fit(X_train, y_train_sobrecosto)

sobrecosto_probs = sobrecosto_model.predict_proba(X_test)[:, 1]
sobrecosto_preds = (sobrecosto_probs > 0.5).astype(int)
sobrecosto_auc = roc_auc_score(y_test_sobrecosto, sobrecosto_probs)
sobrecosto_logloss = log_loss(y_test_sobrecosto, sobrecosto_probs)
sobrecosto_f1 = f1_score(y_test_sobrecosto, sobrecosto_preds)

print(f"ROC-AUC: {sobrecosto_auc:.4f}")
print(f"Log-loss: {sobrecosto_logloss:.4f}")
print(f"F1-Score: {sobrecosto_f1:.4f}")
print(classification_report(y_test_sobrecosto, sobrecosto_preds))


# ---------------------------------------------------------------------------
# 6. Entrenamiento modelo Retraso (XGBoost binario)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("FASE 6: Entrenamiento XGBoost — Probabilidad de Retraso")
print("=" * 60)

retraso_model = xgb.XGBClassifier(
    objective="binary:logistic",
    eval_metric="logloss",
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    random_state=42,
)
retraso_model.fit(X_train, y_train_retraso)

retraso_probs = retraso_model.predict_proba(X_test)[:, 1]
retraso_preds = (retraso_probs > 0.5).astype(int)
retraso_auc = roc_auc_score(y_test_retraso, retraso_probs)
retraso_logloss = log_loss(y_test_retraso, retraso_probs)
retraso_f1 = f1_score(y_test_retraso, retraso_preds)

print(f"ROC-AUC: {retraso_auc:.4f}")
print(f"Log-loss: {retraso_logloss:.4f}")
print(f"F1-Score: {retraso_f1:.4f}")
print(classification_report(y_test_retraso, retraso_preds))


# ---------------------------------------------------------------------------
# 7. SHAP — Explicabilidad del modelo
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("FASE 7: Cálculo de SHAP values (explicabilidad)")
print("=" * 60)

# Crear TreeExplainer para el modelo principal
explainer = shap.TreeExplainer(model)

# Calcular SHAP values sobre una muestra del test set para eficiencia
shap_sample_size = min(500, len(X_test))
X_shap_sample = X_test.sample(n=shap_sample_size, random_state=42)
shap_values = explainer.shap_values(X_shap_sample)

# Guardar el explainer para uso en la API
joblib.dump(explainer, model_path("shap_explainer.pkl"))

# Mapeo de feature names técnicos a nombres legibles
FEATURE_DISPLAY_NAMES = {
    "tipo_proyecto_enc": "Tipo de Proyecto",
    "metodologia_enc": "Metodología",
    "duracion_estimacion": "Duración Estimada (meses)",
    "presupuesto_estimado": "Presupuesto Estimado (USD)",
    "numero_recursos": "Número de Recursos",
    "complejidad_enc": "Complejidad",
    "experiencia_equipo_enc": "Experiencia del Equipo",
    "hitos_clave": "Hitos Clave",
}

# Añadir nombres para tecnologías
for col in tec_df.columns:
    tech_name = col.replace("tec_", "").replace(" ", "")
    FEATURE_DISPLAY_NAMES[col] = f"Tecnología: {tech_name.upper()}"

joblib.dump(FEATURE_DISPLAY_NAMES, model_path("feature_display_names.pkl"))

# Calcular importancia global promedio (media del |SHAP value|)
shap_arr = np.array(shap_values)
if shap_arr.ndim == 3:
    # Multiclase: shape (n_classes, n_samples, n_features) or (n_samples, n_features, n_classes)
    if shap_arr.shape[0] == len(le_riesgo.classes_):
        # (n_classes, n_samples, n_features)
        mean_abs_shap = np.mean([np.abs(shap_arr[c]).mean(axis=0) for c in range(shap_arr.shape[0])], axis=0)
    else:
        # (n_samples, n_features, n_classes)
        mean_abs_shap = np.abs(shap_arr).mean(axis=(0, 2))
else:
    # Binary or single-output: shape (n_samples, n_features)
    mean_abs_shap = np.abs(shap_arr).mean(axis=0)

mean_abs_shap = np.ravel(mean_abs_shap)  # Ensure 1D

feature_importance = pd.DataFrame(
    {"feature": FEATURES, "mean_abs_shap": mean_abs_shap}
).sort_values("mean_abs_shap", ascending=False)

print("\nTop 10 features por importancia SHAP (global):")
for _, row in feature_importance.head(10).iterrows():
    display_name = FEATURE_DISPLAY_NAMES.get(row["feature"], row["feature"])
    print(f"  {display_name}: {row['mean_abs_shap']:.4f}")


# ---------------------------------------------------------------------------
# 8. Guardar modelos, encoders y métricas
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("FASE 8: Persistencia de artefactos")
print("=" * 60)

# Modelos
joblib.dump(model, model_path("modelo_xgb_riesgo_general.pkl"))
joblib.dump(sobrecosto_model, model_path("modelo_xgb_sobrecosto.pkl"))
joblib.dump(retraso_model, model_path("modelo_xgb_retraso.pkl"))

# Encoders
joblib.dump(le_tipo, model_path("le_tipo_proyecto.pkl"))
joblib.dump(le_metodologia, model_path("le_metodologia.pkl"))
joblib.dump(le_complejidad, model_path("le_complejidad.pkl"))
joblib.dump(le_experiencia, model_path("le_experiencia.pkl"))
joblib.dump(mlb, model_path("mlb_tecnologias.pkl"))
joblib.dump(le_riesgo, model_path("le_riesgo_general.pkl"))

# Feature list (necesaria para la API)
joblib.dump(FEATURES, model_path("feature_list.pkl"))

# Métricas para documentación y README
metrics = {
    "dataset": {
        "total_registros": len(df),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "train_balanced_size": len(X_train_bal),
        "features_count": len(FEATURES),
        "clases": list(le_riesgo.classes_),
    },
    "riesgo_general": {
        "best_hyperparams": grid_search.best_params_,
        "cv_f1_weighted": round(float(grid_search.best_score_), 4),
        "test_f1_weighted": round(float(f1_w), 4),
        "test_roc_auc": round(float(roc_auc), 4),
        "test_logloss": round(float(logloss), 4),
        "confusion_matrix": cm.tolist(),
        "classification_report": {
            k: v
            for k, v in report.items()
            if k in list(le_riesgo.classes_) + ["weighted avg", "macro avg"]
        },
    },
    "sobrecosto": {
        "test_roc_auc": round(float(sobrecosto_auc), 4),
        "test_logloss": round(float(sobrecosto_logloss), 4),
        "test_f1": round(float(sobrecosto_f1), 4),
    },
    "retraso": {
        "test_roc_auc": round(float(retraso_auc), 4),
        "test_logloss": round(float(retraso_logloss), 4),
        "test_f1": round(float(retraso_f1), 4),
    },
    "shap": {
        "top_features": [
            {
                "feature": FEATURE_DISPLAY_NAMES.get(row["feature"], row["feature"]),
                "importance": round(float(row["mean_abs_shap"]), 4),
            }
            for _, row in feature_importance.head(10).iterrows()
        ]
    },
    "methodology": {
        "split_strategy": "Stratified 80/20 (split ANTES del balanceo)",
        "balancing": "Upsampling solo en training set",
        "cv_strategy": "Stratified 5-Fold Cross-Validation",
        "hyperparameter_tuning": "GridSearchCV con F1-weighted",
        "explainability": "SHAP TreeExplainer",
    },
}

with open(METRICS_PATH, "w", encoding="utf-8") as f:
    json.dump(metrics, f, indent=2, ensure_ascii=False)

print(f"\nModelos guardados en: {MODELS_DIR}")
print(f"Métricas exportadas en: {METRICS_PATH}")

print("\n" + "=" * 60)
print("ENTRENAMIENTO COMPLETADO EXITOSAMENTE")
print("=" * 60)
print(f"  Riesgo General  — F1: {f1_w:.4f} | AUC: {roc_auc:.4f}")
print(f"  Sobrecosto      — F1: {sobrecosto_f1:.4f} | AUC: {sobrecosto_auc:.4f}")
print(f"  Retraso         — F1: {retraso_f1:.4f} | AUC: {retraso_auc:.4f}")
print("=" * 60)
