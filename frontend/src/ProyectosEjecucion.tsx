import { useEffect, useState } from 'react';
import ModalEditarProyecto from './ModalEditarProyecto';
import ModalResultadoRiesgo from './ModalResultadoRiesgo';
import ModalEnviarEmail from './ModalEnviarEmail';
import ModalFinalizarProyecto from './ModalFinalizarProyecto';
import Toast from './Toast';

// Iconos SVG inline para CRUD
const IconEdit = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19.5 3 21l1.5-4L16.5 3.5z"/></svg>
);
const IconDelete = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
);
const IconGoal = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/></svg>
);

interface Proyecto {
  id: string;
  tipo_proyecto: string;
  metodologia: string;
  duracion_estimacion: string;
  presupuesto_estimado: string;
  numero_recursos: string;
  tecnologias: string;
  complejidad: string;
  experiencia_equipo: string;
  hitos_clave: string;
}

interface ProyectosEjecucionProps {
  onBack?: () => void;
}

const ThemeToggleProyectos = () => {
  const [theme, setTheme] = useState(() => document.documentElement.getAttribute('data-theme') || 'light');
  useEffect(() => {
    const observer = new MutationObserver(() => {
      setTheme(document.documentElement.getAttribute('data-theme') || 'light');
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => observer.disconnect();
  }, []);
  const handleToggle = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    setTheme(newTheme);
  };
  return (
    <button className="btn-ghost" aria-label="Cambiar tema" onClick={handleToggle} title={theme === 'light' ? 'Modo oscuro' : 'Modo claro'} style={{ padding: '0.5rem' }}>
      <span className="icon" style={{transition: 'transform 0.3s'}}>
        {theme === 'light'
          ? (<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>)
          : (<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>)}
      </span>
    </button>
  );
};

const ToastSuccess = ({ message, onClose }: { message: string, onClose: () => void }) => (
  <div className="toast-success" role="alert">
    <span className="icon">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
    </span>
    {message}
    <button style={{marginLeft: '1em', background: 'none', border: 'none', color: 'inherit', fontSize: '1.2em', cursor: 'pointer'}} onClick={onClose} aria-label="Cerrar">×</button>
  </div>
);

// Capitaliza cada palabra, pero respeta siglas (mayúsculas completas)
function capitalizeWords(str: string | undefined | null) {
  if (!str) return '';
  return str.split(' ').map(word =>
    word === word.toUpperCase() ? word : word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
  ).join(' ');
}

export default function ProyectosEjecucion({ onBack }: ProyectosEjecucionProps) {
  const [proyectos, setProyectos] = useState<Proyecto[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [proyectoEdit, setProyectoEdit] = useState<Proyecto | null>(null);
  const [showToast, setShowToast] = useState(false);
  const [modalRiesgoOpen, setModalRiesgoOpen] = useState(false);
  const [resultadoRiesgo, setResultadoRiesgo] = useState<any>(null);
  const [proyectoRiesgo, setProyectoRiesgo] = useState<any>(null);
  const [modalEmailOpen, setModalEmailOpen] = useState(false);
  const [loadingEmail, setLoadingEmail] = useState(false);
  const [toast, setToast] = useState<{message: string, type: 'success'|'error'}|null>(null);
  const [proyectoEmail, setProyectoEmail] = useState<Proyecto | null>(null);
  const [modalFinalizarOpen, setModalFinalizarOpen] = useState(false);
  const [proyectoFinalizar, setProyectoFinalizar] = useState<Proyecto | null>(null);

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/proyectos-ejecucion`)
      .then(res => res.json())
      .then(setProyectos)
      .catch(() => setError('Error al cargar proyectos en ejecución'));
  }, [success]);

  useEffect(() => {
    const observer = new MutationObserver(() => {
      // setTheme(document.documentElement.getAttribute('data-theme') || 'light'); // Eliminado porque setTheme ya no existe
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (success) {
      setShowToast(true);
      const timer = setTimeout(() => setShowToast(false), 2500);
      return () => clearTimeout(timer);
    }
  }, [success]);

  // CRUD: Eliminar proyecto
  const handleDelete = async (id: string) => {
    if (!window.confirm('¿Seguro que deseas eliminar este proyecto?')) return;
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/proyectos-ejecucion/${id}`, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error('Error al eliminar proyecto');
      setSuccess('Proyecto eliminado correctamente');
    } catch (err: any) {
      setError(err.message || 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  // CRUD: Editar proyecto (ahora abre modal)
  const handleEdit = (id: string) => {
    const proyecto = proyectos.find(p => p.id === id) || null;
    setProyectoEdit(proyecto);
    setModalOpen(true);
  };
  const handleSaveEdit = async (proyectoActualizado: Partial<Proyecto>) => {
    if (!proyectoActualizado.id) return;
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/proyectos-ejecucion/${proyectoActualizado.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(proyectoActualizado),
      });
      if (!res.ok) throw new Error('Error al actualizar proyecto');
      setSuccess('Proyecto actualizado correctamente');
      setModalOpen(false);
      setProyectoEdit(null);
    } catch (err: any) {
      setError(err.message || 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  // Predicción de riesgo
  const handlePredecir = async (proyecto: Proyecto) => {
    setResultadoRiesgo(null);
    setProyectoRiesgo(proyecto);
    setModalRiesgoOpen(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...proyecto,
          tecnologias: proyecto.tecnologias,
          duracion_estimacion: Number(proyecto.duracion_estimacion),
          presupuesto_estimado: Number(proyecto.presupuesto_estimado),
          numero_recursos: Number(proyecto.numero_recursos),
          experiencia_equipo: Number(proyecto.experiencia_equipo),
          hitos_clave: Number(proyecto.hitos_clave),
        }),
      });
      if (!res.ok) throw new Error('Error al predecir riesgo');
      const data = await res.json();
      setResultadoRiesgo(data);
    } catch (err) {
      setResultadoRiesgo({ error: 'No se pudo predecir el riesgo.' });
    }
  };

  // Envío de reporte por email desde la tabla
  const handleEnviarEmail = (proyecto: Proyecto) => {
    setProyectoEmail(proyecto);
    setModalEmailOpen(true);
  };
  const handleSendEmail = async (email: string) => {
    if (!proyectoEmail) return;
    setLoadingEmail(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/enviar-reporte-mailhog`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destinatario: email,
          proyecto: {
            ...(() => {
              const { id, ...rest } = proyectoEmail;
              return rest;
            })(),
            tecnologias: Array.isArray(proyectoEmail.tecnologias)
              ? proyectoEmail.tecnologias.join(',')
              : (typeof proyectoEmail.tecnologias === 'string' ? proyectoEmail.tecnologias : ''),
            duracion_estimacion: Number(proyectoEmail.duracion_estimacion),
            presupuesto_estimado: Number(proyectoEmail.presupuesto_estimado),
            numero_recursos: Number(proyectoEmail.numero_recursos),
            experiencia_equipo: Number(proyectoEmail.experiencia_equipo),
            hitos_clave: Number(proyectoEmail.hitos_clave),
          },
          prediccion: null // No hay predicción en la tabla, solo datos del proyecto
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

  // Finalizar proyecto (modal)
  const handleFinalizar = async (id: string, data: { costo_real: string; duracion_real: string; riesgo_general: string }) => {
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/proyectos-ejecucion/${id}/finalizar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error('Error al finalizar proyecto');
      setProyectos(prev => prev.filter(p => p.id !== id)); // Quita el proyecto finalizado de la tabla
      setToast({ message: 'Proyecto finalizado correctamente', type: 'success' });
      setModalFinalizarOpen(false);
      setProyectoFinalizar(null);
    } catch (err: any) {
      setToast({ message: err.message || 'Error desconocido', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Navbar consistente con la vista principal */}
      <nav className="glass-navbar">
        <div className="navbar-logo">
          <strong>RiskPredictor</strong> RPA
        </div>
        <div className="navbar-actions">
          <button onClick={onBack || (() => window.history.back())} className="btn-ghost" title="Volver">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
            <span className="hide-mobile">Volver</span>
          </button>
          <ThemeToggleProyectos />
        </div>
      </nav>
      <ModalEditarProyecto
        proyecto={proyectoEdit}
        open={modalOpen}
        onClose={() => { setModalOpen(false); setProyectoEdit(null); }}
        onSave={handleSaveEdit}
      />
      <ModalResultadoRiesgo
        open={modalRiesgoOpen}
        onClose={() => setModalRiesgoOpen(false)}
        resultado={resultadoRiesgo}
        proyecto={proyectoRiesgo}
      />
      <ModalEnviarEmail
        open={modalEmailOpen}
        onClose={() => setModalEmailOpen(false)}
        onSend={handleSendEmail}
        loading={loadingEmail}
      />
      <ModalFinalizarProyecto
        open={modalFinalizarOpen}
        onClose={() => { setModalFinalizarOpen(false); setProyectoFinalizar(null); }}
        onSave={async (data) => {
          if (proyectoFinalizar) await handleFinalizar(proyectoFinalizar.id, data);
        }}
        loading={loading}
      />
      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}
      <div className="container container-proyectos">
        <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%'}}>
          <h2>Proyectos en Ejecución</h2>
        </div>
        {error && <div style={{color: 'red'}}>{error}</div>}
        {success && <div style={{color: 'green'}}>{success}</div>}
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Tipo</th>
                <th>Metodología</th>
                <th>Duración Estimada</th>
                <th>Presupuesto</th>
                <th>Recursos</th>
                <th>Tecnologías</th>
                <th>Complejidad</th>
                <th>Experiencia</th>
                <th>Hitos</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {proyectos.length === 0 && (
                <tr><td colSpan={10}>No hay proyectos en ejecución.</td></tr>
              )}
              {proyectos.map((p) => (
                <tr key={p.id}>
                  <td>{capitalizeWords(p.tipo_proyecto || '-')}</td>
                  <td>{capitalizeWords(p.metodologia || '-')}</td>
                  <td>{p.duracion_estimacion || '-'}</td>
                  <td>{p.presupuesto_estimado || '-'}</td>
                  <td>{p.numero_recursos || '-'}</td>
                  <td>{(p.tecnologias ? p.tecnologias.split(',').map(capitalizeWords).join(', ') : '-')}</td>
                  <td>{capitalizeWords(p.complejidad || '-')}</td>
                  <td>{p.experiencia_equipo || '-'}</td>
                  <td>{p.hitos_clave || '-'}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'center', flexWrap: 'nowrap' }}>
                      <button onClick={() => handleEdit(p.id)} disabled={loading} title="Editar"
                        style={{ background: 'rgba(59,130,246,0.15)', color: '#3b82f6', border: 'none', borderRadius: 6, padding: '0.4rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', minWidth: 32, height: 32 }}>
                        <IconEdit />
                      </button>
                      <button onClick={() => handleDelete(p.id)} disabled={loading} title="Eliminar"
                        style={{ background: 'rgba(244,63,94,0.15)', color: '#f43f5e', border: 'none', borderRadius: 6, padding: '0.4rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', minWidth: 32, height: 32 }}>
                        <IconDelete />
                      </button>
                      <button onClick={() => handlePredecir(p)} disabled={loading} title="Predecir riesgo"
                        style={{ background: 'rgba(16,185,129,0.15)', color: '#10b981', border: 'none', borderRadius: 6, padding: '0.4rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', minWidth: 32, height: 32 }}>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 19V6M5 12l7-7 7 7"/></svg>
                      </button>
                      <button onClick={() => handleEnviarEmail(p)} disabled={loading} title="Enviar email"
                        style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b', border: 'none', borderRadius: 6, padding: '0.4rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', minWidth: 32, height: 32 }}>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><polyline points="22,6 12,13 2,6"/></svg>
                      </button>
                      <button onClick={() => { setProyectoFinalizar(p); setModalFinalizarOpen(true); }} disabled={loading} title="Finalizar"
                        style={{ background: 'rgba(139,92,246,0.15)', color: '#8b5cf6', border: 'none', borderRadius: 6, padding: '0.4rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', minWidth: 32, height: 32 }}>
                        <IconGoal />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {showToast && <ToastSuccess message={success} onClose={() => setShowToast(false)} />}
    </>
  );
}
