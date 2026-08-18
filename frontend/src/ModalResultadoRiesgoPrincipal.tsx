import React, { useState } from 'react';
import ReportePDFButton from './ReportePDFButton';
import ModalEnviarEmail from './ModalEnviarEmail';
import Toast from './Toast';

interface FactorExplicabilidad {
  factor: string;
  impacto_shap: number;
  direccion: string;
  descripcion: string;
}

interface ResultadoRiesgo {
  riesgo_general: string;
  probabilidades_riesgo: Record<string, number>;
  probabilidad_sobrecosto: number;
  probabilidad_retraso: number;
  factores_explicabilidad?: FactorExplicabilidad[];
}

interface ModalResultadoRiesgoProps {
  open: boolean;
  onClose: () => void;
  resultado: ResultadoRiesgo | null;
  proyecto: any;
}

function getRiskColor(level: string): string {
  const l = level.toLowerCase();
  if (l === 'alto') return '#ef4444';
  if (l === 'medio') return '#f59e0b';
  return '#22c55e';
}

function getRiskIcon(level: string): string {
  const l = level.toLowerCase();
  if (l === 'alto') return '🔴';
  if (l === 'medio') return '🟡';
  return '🟢';
}

function getBarColor(value: number): string {
  if (value > 0.6) return '#ef4444';
  if (value > 0.3) return '#f59e0b';
  return '#22c55e';
}

const ModalResultadoRiesgo: React.FC<ModalResultadoRiesgoProps> = ({ open, onClose, resultado, proyecto }) => {
  const [modalEmailOpen, setModalEmailOpen] = useState(false);
  const [loadingEmail, setLoadingEmail] = useState(false);
  const [savingProject, setSavingProject] = useState(false);
  const [projectSaved, setProjectSaved] = useState(false);
  const [toast, setToast] = useState<{message: string, type: 'success'|'error'}|null>(null);

  const handleSendEmail = async (email: string) => {
    setLoadingEmail(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/enviar-reporte-mailhog`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destinatario: email,
          proyecto: {
            ...proyecto,
            tecnologias: Array.isArray(proyecto.tecnologias)
              ? proyecto.tecnologias.join(',')
              : (typeof proyecto.tecnologias === 'string' ? proyecto.tecnologias : ''),
            duracion_estimacion: Number(proyecto.duracion_estimacion),
            presupuesto_estimado: Number(proyecto.presupuesto_estimado),
            numero_recursos: Number(proyecto.numero_recursos),
            experiencia_equipo: Number(proyecto.experiencia_equipo),
            hitos_clave: Number(proyecto.hitos_clave),
          },
          prediccion: resultado
        })
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'No se pudo enviar el email. Verifica la configuración SMTP.');
      }
      setToast({ message: 'Reporte enviado exitosamente', type: 'success' });
      setModalEmailOpen(false);
    } catch (e: any) {
      setToast({ message: e.message || 'Error al enviar email', type: 'error' });
    } finally {
      setLoadingEmail(false);
    }
  };

  const handleSaveProject = async () => {
    setSavingProject(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/proyectos-ejecucion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...proyecto,
          tecnologias: Array.isArray(proyecto.tecnologias)
            ? proyecto.tecnologias.join(',')
            : (typeof proyecto.tecnologias === 'string' ? proyecto.tecnologias : ''),
          duracion_estimacion: Number(proyecto.duracion_estimacion),
          presupuesto_estimado: Number(proyecto.presupuesto_estimado),
          numero_recursos: Number(proyecto.numero_recursos),
          experiencia_equipo: Number(proyecto.experiencia_equipo),
          hitos_clave: Number(proyecto.hitos_clave),
        })
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Error al guardar proyecto');
      }
      setToast({ message: 'Proyecto guardado exitosamente', type: 'success' });
      setProjectSaved(true);
    } catch (e: any) {
      setToast({ message: e.message || 'Error al guardar', type: 'error' });
    } finally {
      setSavingProject(false);
    }
  };

  if (!open || !resultado) return null;

  const riskColor = getRiskColor(resultado.riesgo_general);
  const riskIcon = getRiskIcon(resultado.riesgo_general);

  return (
    <>
      <div className="modal-editar-proyecto-overlay">
        <div className="modal-resultado-premium">
          
          {/* Header */}
          <div className="modal-resultado-header">
            <div>
              <h3>Resultado de Predicción</h3>
              <p>Motor Analítico — XGBoost + Explainable AI (SHAP)</p>
            </div>
            <button className="modal-close-btn" onClick={onClose}>✕</button>
          </div>

          {/* Body */}
          <div className="modal-resultado-body">
            
            {/* Risk Badge */}
            <div className="risk-badge" style={{ 
              borderColor: riskColor,
              color: riskColor,
            }}>
              <span style={{ fontSize: '1.4rem' }}>{riskIcon}</span>
              Riesgo {resultado.riesgo_general}
            </div>

            {/* Probabilidades */}
            <div className="prob-section">
              <p className="prob-label">Distribución de Probabilidades</p>
              {Object.entries(resultado.probabilidades_riesgo).map(([key, value]) => {
                const pct = (value * 100).toFixed(1);
                const barColor = getBarColor(value);
                return (
                  <div key={key} className="prob-row">
                    <div className="prob-row-header">
                      <span className="prob-name">{key}</span>
                      <span className="prob-value" style={{ color: barColor }}>{pct}%</span>
                    </div>
                    <div className="prob-bar-track">
                      <div className="prob-bar-fill" style={{
                        width: `${Math.max(Number(pct), 2)}%`,
                        background: barColor,
                      }} />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Metric Cards */}
            <div className="metric-cards">
              <div className="metric-card metric-card-rose">
                <span className="metric-label">Sobrecosto</span>
                <span className="metric-value" style={{ color: getBarColor(resultado.probabilidad_sobrecosto) }}>
                  {(resultado.probabilidad_sobrecosto * 100).toFixed(1)}%
                </span>
              </div>
              <div className="metric-card metric-card-amber">
                <span className="metric-label">Retraso</span>
                <span className="metric-value" style={{ color: getBarColor(resultado.probabilidad_retraso) }}>
                  {(resultado.probabilidad_retraso * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Explainable AI (SHAP Factors) */}
            {resultado.factores_explicabilidad && resultado.factores_explicabilidad.length > 0 && (
              <div className="shap-factors-section" style={{ marginTop: '0.85rem', marginBottom: '0.85rem', textAlign: 'left' }}>
                <p className="prob-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', fontWeight: 600 }}>
                  <span>🧠</span> <strong>Explicabilidad IA (Top Factores SHAP)</strong>
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', marginTop: '0.4rem' }}>
                  {resultado.factores_explicabilidad.map((f, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontSize: '0.82rem',
                        padding: '0.4rem 0.65rem',
                        borderRadius: '6px',
                        background: f.direccion === 'incrementa_riesgo' ? 'rgba(239, 68, 68, 0.08)' : 'rgba(34, 197, 94, 0.08)',
                        border: `1px solid ${f.direccion === 'incrementa_riesgo' ? 'rgba(239, 68, 68, 0.25)' : 'rgba(34, 197, 94, 0.25)'}`,
                      }}
                    >
                      <span style={{ fontWeight: 500 }}>
                        {f.direccion === 'incrementa_riesgo' ? '🔺' : '🔻'} {f.factor}
                      </span>
                      <span style={{
                        fontWeight: 600,
                        fontSize: '0.78rem',
                        color: f.direccion === 'incrementa_riesgo' ? '#ef4444' : '#22c55e'
                      }}>
                        {f.impacto_shap > 0 ? `+${f.impacto_shap.toFixed(2)}` : f.impacto_shap.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Save Project */}
            <div className="modal-resultado-actions" style={{ marginBottom: '0.75rem' }}>
              <button
                type="button"
                className="btn-save-project"
                onClick={handleSaveProject}
                disabled={savingProject || projectSaved}
              >
                {projectSaved ? '✅ Guardado' : savingProject ? '⏳ Guardando...' : '💾 Guardar Proyecto'}
              </button>
            </div>

            {/* Actions */}
            <div className="modal-resultado-actions">
              <ReportePDFButton formData={{
                ...proyecto,
                tecnologias: Array.isArray(proyecto.tecnologias)
                  ? proyecto.tecnologias
                  : (typeof proyecto.tecnologias === 'string' ? proyecto.tecnologias.split(',').map((t: string) => t.trim()) : []),
              }} />
              <button type="button" className="btn-email" onClick={() => setModalEmailOpen(true)}>
                📧 Enviar por Email
              </button>
            </div>
          </div>
        </div>
      </div>
      <ModalEnviarEmail
        open={modalEmailOpen}
        onClose={() => setModalEmailOpen(false)}
        onSend={handleSendEmail}
        loading={loadingEmail}
      />
      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}
    </>
  );
};

export default ModalResultadoRiesgo;
