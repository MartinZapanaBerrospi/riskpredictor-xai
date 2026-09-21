import pandas as pd
import numpy as np
import random
import os

# Semilla para reproducibilidad
definir_semilla = 42
np.random.seed(definir_semilla)
random.seed(definir_semilla)

DATA_DIR = os.path.dirname(__file__)

N = 20000  # Número de proyectos sintéticos

complejidades = ['baja', 'media', 'alta']
tecnologias_posibles = ['cloud', 'big data', 'IA', 'IoT', 'blockchain', 'mobile', 'web']
tipos_proyecto = [
    'desarrollo software', 'migración', 'implementación ERP', 'integración sistemas', 'automatización RPA', 'modernización', 'soporte TI'
]

# Generación realista de proyectos TI sintéticos SOLO CON INPUTS DISPONIBLES ANTES DEL PROYECTO
def generar_proyecto():
    tipo = random.choice(tipos_proyecto)
    # Asignar metodología según tipo de proyecto
    if tipo in ['implementación ERP', 'integración sistemas']:
        metodologia = random.choices(['cascada', 'agile'], weights=[0.7, 0.3])[0]
    elif tipo in ['automatización RPA', 'desarrollo software', 'modernización']:
        metodologia = random.choices(['scrum', 'kanban', 'agile'], weights=[0.6, 0.2, 0.2])[0]
    else:  # soporte TI, migración
        metodologia = random.choices(['kanban', 'cascada', 'agile'], weights=[0.5, 0.3, 0.2])[0]

    if tipo == 'implementación ERP':
        duracion = int(np.random.normal(28, 4))
        presupuesto = int(np.random.normal(1200000, 250000))
        recursos = int(np.random.normal(20, 5))
        complejidad = 'alta'
        tecnologias = random.sample(tecnologias_posibles, k=np.random.randint(2, 5))
    elif tipo == 'migración':
        duracion = int(np.random.normal(12, 3))
        presupuesto = int(np.random.normal(350000, 100000))
        recursos = int(np.random.normal(7, 2))
        complejidad = random.choice(['baja', 'media'])
        tecnologias = random.sample(tecnologias_posibles, k=1)
    elif tipo == 'automatización RPA':
        duracion = int(np.random.normal(10, 3))
        presupuesto = int(np.random.normal(300000, 80000))
        recursos = int(np.random.normal(6, 2))
        complejidad = random.choice(['media', 'alta'])
        tecnologias = random.sample(tecnologias_posibles, k=2)
    elif tipo == 'desarrollo software':
        duracion = int(np.random.normal(15, 5))
        presupuesto = int(np.random.normal(600000, 200000))
        recursos = int(np.random.normal(12, 4))
        complejidad = random.choice(['media', 'alta'])
        tecnologias = random.sample(tecnologias_posibles, k=np.random.randint(1, 4))
    elif tipo == 'integración sistemas':
        duracion = int(np.random.normal(16, 4))
        presupuesto = int(np.random.normal(500000, 150000))
        recursos = int(np.random.normal(10, 3))
        complejidad = random.choice(['media', 'alta'])
        tecnologias = random.sample(tecnologias_posibles, k=2)
    elif tipo == 'modernización':
        duracion = int(np.random.normal(12, 3))
        presupuesto = int(np.random.normal(400000, 100000))
        recursos = int(np.random.normal(8, 2))
        complejidad = random.choice(['media', 'alta'])
        tecnologias = random.sample(tecnologias_posibles, k=2)
    else:  # soporte TI
        duracion = int(np.random.normal(9, 2))
        presupuesto = int(np.random.normal(200000, 50000))
        recursos = int(np.random.normal(5, 1))
        complejidad = 'baja'
        tecnologias = random.sample(tecnologias_posibles, k=1)

    # Limitar valores a rangos razonables
    duracion = max(6, min(duracion, 36))
    presupuesto = max(100000, min(presupuesto, 2000000))
    recursos = max(3, min(recursos, 30))

    experiencia = int(np.random.normal(8, 3))  # años de experiencia promedio
    experiencia = max(1, min(experiencia, 15))
    hitos = np.random.randint(2, 11)

    # Desviación de costo y plazo.
    #
    # El proceso generador es deliberadamente explícito: la desviación ESPERADA
    # depende de factores observables del proyecto (complejidad, experiencia del
    # equipo, presupuesto por recurso, cantidad de tecnologías, metodología y
    # duración), y sobre esa media se añade ruido aleatorio.
    #
    # Antes, la media era 1.0 para todos los proyectos y solo cambiaba la
    # varianza: eso hacía que el sobrecosto fuera equivalente a lanzar una
    # moneda y ningún modelo podía superar el azar (ROC-AUC ~ 0.5).
    presupuesto_por_recurso = presupuesto / max(recursos, 1)
    n_tecnologias = len(tecnologias)

    sesgo_costo = 0.0
    sesgo_costo += {'alta': 0.09, 'media': 0.04, 'baja': 0.0}[complejidad]
    sesgo_costo += 0.06 if experiencia < 5 else (-0.03 if experiencia > 10 else 0.0)
    sesgo_costo += 0.05 if presupuesto_por_recurso < 40000 else 0.0
    sesgo_costo += 0.02 * max(0, n_tecnologias - 2)
    sesgo_costo += 0.03 if metodologia == 'cascada' else (-0.02 if metodologia in ('scrum', 'kanban') else 0.0)
    sesgo_costo += 0.03 if tipo in ('implementación ERP', 'integración sistemas') else 0.0

    sesgo_tiempo = 0.0
    sesgo_tiempo += {'alta': 0.10, 'media': 0.04, 'baja': 0.0}[complejidad]
    sesgo_tiempo += 0.07 if experiencia < 5 else (-0.03 if experiencia > 10 else 0.0)
    sesgo_tiempo += 0.05 if duracion < 12 and complejidad == 'alta' else 0.0
    sesgo_tiempo += 0.02 * max(0, n_tecnologias - 2)
    sesgo_tiempo += 0.04 if metodologia == 'cascada' else (-0.02 if metodologia in ('scrum', 'kanban') else 0.0)
    sesgo_tiempo += 0.02 if hitos >= 8 else 0.0

    ruido = 0.08 + (0.05 if complejidad == 'alta' else 0) + (0.05 if experiencia < 5 else 0)
    desviacion_costo = np.random.normal(0.97 + sesgo_costo, ruido)
    desviacion_tiempo = np.random.normal(0.96 + sesgo_tiempo, ruido)
    costo_real = int(presupuesto * desviacion_costo)
    duracion_real = int(duracion * desviacion_tiempo)
    costo_real = max(100000, costo_real)
    duracion_real = max(6, duracion_real)

    return {
        'tipo_proyecto': tipo,
        'metodologia': metodologia,
        'duracion_estimacion': duracion,
        'presupuesto_estimado': presupuesto,
        'numero_recursos': recursos,
        'tecnologias': ','.join(tecnologias),
        'complejidad': complejidad,
        'experiencia_equipo': experiencia,
        'hitos_clave': hitos,
        'costo_real': costo_real,
        'duracion_real': duracion_real
    }

proyectos = [generar_proyecto() for _ in range(N)]
df = pd.DataFrame(proyectos)

# Calcular sobrecosto y retraso
df['sobrecosto'] = (df['costo_real'] > df['presupuesto_estimado']).astype(int)
df['retraso'] = (df['duracion_real'] > df['duracion_estimacion']).astype(int)

# Probabilidad sintética de sobrecosto y retraso
df['riesgo_costo_prob'] = df['sobrecosto'] * np.random.uniform(0.6, 1.0, size=len(df)) + (1 - df['sobrecosto']) * np.random.uniform(0.0, 0.4, size=len(df))
df['riesgo_tiempo_prob'] = df['retraso'] * np.random.uniform(0.6, 1.0, size=len(df)) + (1 - df['retraso']) * np.random.uniform(0.0, 0.4, size=len(df))

# Riesgo general basado en reglas
conditions = [
    (df['riesgo_costo_prob'] > 0.7) & (df['riesgo_tiempo_prob'] > 0.7),
    (df['riesgo_costo_prob'] > 0.7) | (df['riesgo_tiempo_prob'] > 0.7)
]
choices = ['Alto', 'Medio']
df['riesgo_general'] = np.select(conditions, choices, default='Bajo')

# Reglas adicionales para riesgo más realista
# 1. Experiencia baja y complejidad alta => más riesgo
exp_baja_alta = (df['experiencia_equipo'] < 5) & (df['complejidad'] == 'alta')
# 2. Muchas tecnologías => más riesgo
muchas_tecnos = df['tecnologias'].apply(lambda x: len(x.split(',')) >= 3)
# 3. Tipo de proyecto riesgoso
proy_riesgoso = df['tipo_proyecto'].isin(['implementación ERP', 'integración sistemas'])
# 4. Presupuesto por recurso bajo
presup_x_recurso_bajo = (df['presupuesto_estimado'] / df['numero_recursos']) < 40000
# 5. Duración corta y complejidad alta
corta_alta = (df['duracion_estimacion'] < 12) & (df['complejidad'] == 'alta')

# Sumar puntos de riesgo
df['puntos_riesgo'] = (
    exp_baja_alta.astype(int) +
    muchas_tecnos.astype(int) +
    proy_riesgoso.astype(int) +
    presup_x_recurso_bajo.astype(int) +
    corta_alta.astype(int)
)

# Ajustar probabilidad de riesgo
# Si puntos_riesgo >=3, aumentar probabilidad de riesgo alto
cond_alto = (df['puntos_riesgo'] >= 3) | ((df['riesgo_costo_prob'] > 0.7) & (df['riesgo_tiempo_prob'] > 0.7))
cond_medio = (df['puntos_riesgo'] == 2) | ((df['riesgo_costo_prob'] > 0.7) | (df['riesgo_tiempo_prob'] > 0.7))
df['riesgo_general'] = np.select([cond_alto, cond_medio], ['Alto', 'Medio'], default='Bajo')

# Rutas absolutas para guardar los CSV dentro de la carpeta data/
path_full = os.path.join(DATA_DIR, 'synthetic_data_with_outputs.csv')
path_inputs = os.path.join(DATA_DIR, 'synthetic_data.csv')

# Guardar todos los campos relevantes en synthetic_data_with_outputs.csv
cols_full = [
    'tipo_proyecto', 'metodologia', 'duracion_estimacion', 'presupuesto_estimado', 'numero_recursos',
    'tecnologias', 'complejidad', 'experiencia_equipo', 'hitos_clave',
    'costo_real', 'duracion_real',
    'sobrecosto', 'retraso',
    'riesgo_costo_prob', 'riesgo_tiempo_prob',
    'puntos_riesgo', 'riesgo_general'
]
df[cols_full].to_csv(path_full, index=False)

# Guardar solo los inputs en synthetic_data.csv (sin sobrecosto, retraso ni puntos_riesgo)
inputs_cols = [
    'tipo_proyecto', 'metodologia', 'duracion_estimacion', 'presupuesto_estimado', 'numero_recursos',
    'tecnologias', 'complejidad', 'experiencia_equipo', 'hitos_clave',
    'costo_real', 'duracion_real'
]
df[inputs_cols].to_csv(path_inputs, index=False)

print('¡Datos completos guardados en synthetic_data_with_outputs.csv y solo inputs en synthetic_data.csv!')
