from datetime import datetime
import re
from fpdf import FPDF


def capitalize_text(text):
    if not isinstance(text, str):
        return text
    text = str(text).replace(",", ", ")
    text = re.sub(r"\s+", " ", text).strip()

    def smart_cap(word):
        clean_word = word.strip(",.")
        if clean_word.isupper() and len(clean_word) > 2:
            return word
        if len(clean_word) <= 2:
            return word.upper()
        return word.capitalize()

    return " ".join(smart_cap(w) for w in text.split(" "))


class PDFReport(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(24, 43, 73)
        self.cell(0, 8, "RiskPredictor RPA — Informe Ejecutivo de Riesgos", ln=True, align="L")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(110, 120, 135)
        self.cell(0, 6, f"Generado por Motor Analítico AI | Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="L")
        self.ln(2)
        self.set_draw_color(37, 99, 235)
        self.set_line_width(0.6)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140, 150, 165)
        self.cell(0, 8, f"RiskPredictor RPA  |  Página {self.page_no()}", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(24, 43, 73)
        self.cell(0, 8, title, ln=True)
        self.ln(1)

    def section_body(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(45, 55, 72)
        self.multi_cell(0, 6, text)
        self.ln(2)

    def add_table(self, data_dict):
        self.set_font("Helvetica", "", 10)
        self.set_fill_color(243, 246, 252)
        for k, v in data_dict.items():
            label = k.replace("_", " ").capitalize()
            if isinstance(v, str):
                v = capitalize_text(v)
            elif isinstance(v, list):
                v = ", ".join([capitalize_text(x) for x in v])
            self.cell(65, 7, f"  {label}", 1, 0, "L", True)
            self.cell(0, 7, f"  {str(v)}", 1, 1, "L", False)
        self.ln(3)

    def add_probabilities(self, prob_dict):
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(235, 240, 250)
        self.cell(65, 7, "  Nivel de Riesgo", 1, 0, "L", True)
        self.cell(0, 7, "  Probabilidad Asignada por IA", 1, 1, "L", True)
        self.set_font("Helvetica", "", 9)
        for clase, prob in prob_dict.items():
            self.cell(65, 6, f"  {clase}", 1, 0, "L", False)
            self.cell(0, 6, f"  {prob * 100:.1f} %", 1, 1, "L", False)
        self.ln(3)

    def add_shap_factors(self, factores):
        if not factores:
            return
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(235, 240, 250)
        self.cell(75, 7, "  Factor Determinante", 1, 0, "L", True)
        self.cell(40, 7, "  Impacto SHAP", 1, 0, "C", True)
        self.cell(0, 7, "  Efecto sobre el Riesgo", 1, 1, "L", True)
        self.set_font("Helvetica", "", 9)
        for f in factores:
            factor_name = str(f.get("factor", ""))
            impact = float(f.get("impacto_shap", 0))
            direccion = f.get("direccion", "")
            efecto = "Incrementa Riesgo" if "incrementa" in direccion else "Reduce / Mitiga Riesgo"
            self.cell(75, 6, f"  {factor_name}", 1, 0, "L", False)
            self.cell(40, 6, f"  {impact:+.4f}", 1, 0, "C", False)
            self.cell(0, 6, f"  {efecto}", 1, 1, "L", False)
        self.ln(3)


def generar_reporte_pdf(proyecto, prediccion=None, filename="reporte_riesgo.pdf"):
    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # 1. Parámetros del Proyecto
    pdf.section_title("1. Parámetros Estructurales del Proyecto")
    pdf.add_table(proyecto)

    # 2. Diagnóstico Predictivo
    pdf.section_title("2. Diagnóstico Predictivo Multi-Objetivo")
    if prediccion and isinstance(prediccion, dict) and prediccion.get("riesgo_general"):
        pdf.section_body(f"Nivel de Riesgo Predictivo Asignado: {prediccion['riesgo_general'].upper()}")
        if "probabilidades" in prediccion and prediccion["probabilidades"]:
            pdf.add_probabilities(prediccion["probabilidades"])
        
        prob_s = prediccion.get("probabilidad_sobrecosto", 0) * 100
        prob_r = prediccion.get("probabilidad_retraso", 0) * 100
        pdf.section_body(f"• Probabilidad Estimada de Sobrecosto Presupuestario: {prob_s:.1f}%\n• Probabilidad Estimada de Desviación en Cronograma (Retraso): {prob_r:.1f}%")
    else:
        pdf.section_body("No se ha registrado una evaluación inferencial previa.")

    # 3. Explicabilidad Algorítmica (SHAP)
    factores = prediccion.get("factores_explicabilidad") if prediccion else []
    if factores:
        pdf.section_title("3. Explicabilidad Algorítmica (Top Drivers de Riesgo — SHAP)")
        pdf.section_body("Desglose cuantitativo de los factores que tuvieron mayor peso en la decisión del modelo:")
        pdf.add_shap_factors(factores)

    # 4. Análisis Ejecutivo y Recomendaciones PMO
    pdf.section_title("4. Análisis Estratégico y Recomendaciones PMO")
    interpretacion = ""
    riesgo = (prediccion.get("riesgo_general") or "").lower() if prediccion else ""

    if riesgo == "alto":
        interpretacion += (
            "ESTADO CRÍTICO (Riesgo Alto):\n"
            "El modelo detecta una combinación de variables con alta probabilidad de desviación financiera u operativa. "
            "Recomendaciones clave:\n"
            "1. Auditoría inmediata del alcance y congelamiento de requerimientos no esenciales (scope creep).\n"
            "2. Establecer reservas de contingencia presupuestaria superiores al 15%.\n"
            "3. Implementar cadencias diarias de seguimiento (Standup + Burndown tracking).\n\n"
        )
    elif riesgo == "medio":
        interpretacion += (
            "ALERTA PREVENTIVA (Riesgo Moderado):\n"
            "El proyecto presenta desafíos técnicos que requieren mitigación proactiva. "
            "Recomendaciones clave:\n"
            "1. Reforzar el control sobre la asignación de recursos y niveles de seniority técnico.\n"
            "2. Realizar revisiones quincenales de hitos y acuerdos de nivel de servicio (SLAs).\n\n"
        )
    elif riesgo == "bajo":
        interpretacion += (
            "ESTADO SALUDABLE (Riesgo Controlado):\n"
            "Los parámetros estructurales se alinean con perfiles históricos de alta tasa de éxito. "
            "Recomendaciones clave:\n"
            "1. Mantener las prácticas estándar de entrega continua y gestión de calidad.\n"
            "2. Monitorear dependencias externas sin alterar la planificación base.\n\n"
        )
    else:
        interpretacion += "Sin datos suficientes para emitir recomendaciones específicas.\n\n"

    interpretacion += (
        "Descargo de Responsabilidad: Este informe ha sido emitido de manera automatizada por el motor analítico "
        "RiskPredictor RPA mediante algoritmos XGBoost y explicabilidad SHAP. Su objetivo es brindar soporte a la toma "
        "de decisiones de la PMO y comités directivos."
    )
    pdf.section_body(interpretacion)

    pdf.output(filename)
    print(f"[PDF] Reporte generado exitosamente: {filename}")
