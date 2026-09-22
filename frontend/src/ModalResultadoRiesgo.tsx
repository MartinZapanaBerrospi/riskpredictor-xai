import React, { useState } from 'react';
import ReportePDFButton from './ReportePDFButton';
import ModalEnviarEmail from './ModalEnviarEmail';
import Toast from './Toast';

interface ResultadoRiesgo {
  riesgo_general: string;
  probabilidades_riesgo: Record<string, number>;
  probabilidad_sobrecosto: number;
  probabilidad_retraso: number;
}

interface ModalResultadoRiesgoProps {
  open: boolean;
  onClose: () => void;
  resultado: ResultadoRiesgo | null;
  proyecto: any;
}

const ModalResultadoRiesgo: React.FC<ModalResultadoRiesgoProps> = ({ open, onClose, resultado, proyecto }) => {
  const [modalEmailOpen, setModalEmailOpen] = useState(false);
  const [loadingEmail, setLoadingEmail] = useState(false);
  const [toast, setToast] = useState<{message: string, type: 'success'|'error'}|null>(null);

  const handleSendEmail = async (email: string) => {
    setLoadingEmail(true);
    try {
      // Adaptar la estructura de predicción para el backend
      const prediccion = resultado
        ? {
            riesgo_general: resultado.riesgo_general,
            probabilidades: resultado.probabilidades_riesgo, // clave correcta para backend
            probabilidad_sobrecosto: resultado.probabilidad_sobrecosto,
            probabilidad_retraso: resultado.probabilidad_retraso
          }
        : null;
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
          prediccion
        })
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'No se pudo enviar el email');
      }
      setToast({ message: 'Reporte enviado exitosamente', type: 'success' });
      setModalEmailOpen(false);
    } catch (e: any) {
      setToast({ message: e.message || 'Error al enviar email', type: 'error' });
    } finally {
      setLoadingEmail(false);
    }
  };

  if (!open || !resultado) return null;
  return (
    <>
      <div className="modal-editar-proyecto-overlay">
        <div className="modal-editar-proyecto" style={{maxWidth: 500}}>
          <h3>Resultado de Predicción</h3>
          <div className="result" style={{margin: 0}}>
            <p><b>Riesgo General:</b> {resultado.riesgo_general}</p>
            <p><b>Probabilidades de Riesgo:</b></p>
            <ul>
              {Object.entries(resultado.probabilidades_riesgo).map(([k, v]) => (
                <li key={k}>{k}: {(v * 100).toFixed(1)}%</li>
              ))}
            </ul>
            <p><b>Probabilidad de Sobrecosto:</b> {(resultado.probabilidad_sobrecosto * 100).toFixed(1)}%</p>
            <p><b>Probabilidad de Retraso:</b> {(resultado.probabilidad_retraso * 100).toFixed(1)}%</p>
          </div>
          <div className="modal-editar-proyecto-actions" style={{gap: 8}}>
            <ReportePDFButton formData={{
              ...proyecto,
              tecnologias: Array.isArray(proyecto.tecnologias)
                ? proyecto.tecnologias
                : (typeof proyecto.tecnologias === 'string' ? proyecto.tecnologias.split(',').map((t: string) => t.trim()) : []),
            }} />
            <button type="button" onClick={() => setModalEmailOpen(true)} className="primary" style={{marginTop: 16}}>
              Enviar por email
            </button>
            <button type="button" onClick={onClose} className="cancel">Cerrar</button>
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
