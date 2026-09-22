import { useState, useEffect } from 'react';
import './App.css';
import ProyectosEjecucion from './ProyectosEjecucion';
import ModalResultadoRiesgoPrincipal from './ModalResultadoRiesgoPrincipal';
import Toast from './Toast';

const initialState = {
  tipo_proyecto: '',
  metodologia: '',
  duracion_estimacion: '',
  presupuesto_estimado: '',
  numero_recursos: '',
  tecnologias: [],
  complejidad: 'media',
  experiencia_equipo: '',
  hitos_clave: '',
};

type Opciones = {
  tipo_proyecto: string[];
  tecnologias: string[];
  metodologia?: string[];
};

function ThemeToggle() {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);
  return (
    <button
      className="theme-toggle"
      aria-label="Cambiar tema"
      onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
      title={theme === 'light' ? 'Modo oscuro' : 'Modo claro'}
    >
      <span className="icon" style={{transition: 'transform 0.3s'}}>
        {theme === 'light'
          ? (<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>)
          : (<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>)}
      </span>
    </button>
  );
}

function App() {
  const [form, setForm] = useState<any>(initialState);
  const [loading, setLoading] = useState(false);

  const [opciones, setOpciones] = useState<Opciones>({
    tipo_proyecto: ["desarrollo software", "migración", "implementación ERP", "integración sistemas", "automatización RPA", "modernización", "soporte TI"],
    tecnologias: ["cloud", "big data", "IA", "IoT", "blockchain", "mobile", "web"],
    metodologia: ["agile", "scrum", "kanban", "cascada"]
  });
  const [view, setView] = useState<'form' | 'proyectos'>('form');
  const [modalRiesgoOpen, setModalRiesgoOpen] = useState(false);
  const [resultadoRiesgo, setResultadoRiesgo] = useState<any>(null);
  const [formPrediccion, setFormPrediccion] = useState<any>(null);
  const [toast, setToast] = useState<{message: string, type?: 'success'|'error'}|null>(null);

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/opciones-formulario`)
      .then(res => res.json())
      .then(data => {
        if (data && data.tipo_proyecto && data.tipo_proyecto.length > 0) {
          setOpciones(data);
        }
      })
      .catch(console.error);
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, checked } = e.target as HTMLInputElement;
    if (name === 'tecnologias') {
      if (checked) {
        setForm({ ...form, tecnologias: [...form.tecnologias, value] });
      } else {
        setForm({ ...form, tecnologias: form.tecnologias.filter((t: string) => t !== value) });
      }
    } else {
      setForm({ ...form, [name]: value });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.tecnologias || form.tecnologias.length === 0) {
      setToast({ message: 'Debes seleccionar al menos una tecnología.', type: 'error' });
      return;
    }
    setLoading(true);
    setResultadoRiesgo(null);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...form,
          tecnologias: form.tecnologias.join(','),
          duracion_estimacion: Number(form.duracion_estimacion),
          presupuesto_estimado: Number(form.presupuesto_estimado),
          numero_recursos: Number(form.numero_recursos),
          experiencia_equipo: Number(form.experiencia_equipo),
          hitos_clave: Number(form.hitos_clave),
        }),
      });
      if (!response.ok) throw new Error('Error en la predicción');
      const data = await response.json();
      setResultadoRiesgo(data);
      setFormPrediccion(form);
      setModalRiesgoOpen(true);
    } catch (err: any) {
      setToast({ message: err.message || 'Error desconocido', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleLimpiarCampos = () => {
    setForm(initialState);
    setResultadoRiesgo(null);
    setFormPrediccion(null);
  };


  if (view === 'proyectos') {
    return (
      <>
        <ProyectosEjecucion onBack={() => setView('form')} />
      </>
    );
  }

  return (
    <>
      {/* Top Navbar / Utility Bar minimalista */}
      <nav className="glass-navbar">
        <div className="navbar-logo">
          <strong>RiskPredictor</strong> RPA
        </div>
        <div className="navbar-actions">
          <button onClick={() => setView('proyectos')} className="btn-ghost">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
            <span className="hide-mobile">Proyectos</span>
          </button>
          <ThemeToggle />
        </div>
      </nav>

      <main className="container main-content-wrapper">
        <div className="header-titles">
          <h1>Motor Analítico de Riesgos</h1>
          <p className="subtitle">Configura los parámetros del proyecto TI para generar una predicción impulsada por Inteligencia Artificial (XGBoost).</p>
        </div>
        
        <form onSubmit={handleSubmit} className="risk-form">
        <div className="form-group">
          <label>Tipo de Proyecto:
            <select name="tipo_proyecto" value={form.tipo_proyecto} onChange={handleChange} required>
              <option value="">Seleccione...</option>
              {opciones.tipo_proyecto.map((op) => (
                <option key={op} value={op}>{op}</option>
              ))}
            </select>
          </label>
        </div>
        <div className="form-group">
          <label>Metodología:
            <select name="metodologia" value={form.metodologia} onChange={handleChange} required>
              <option value="">Seleccione...</option>
              {opciones.metodologia && opciones.metodologia.map((op) => (
                <option key={op} value={op}>{op}</option>
              ))}
            </select>
          </label>
        </div>
        <div className="form-group">
          <label>Duración Estimada (meses):
            <input name="duracion_estimacion" type="number" min="1" value={form.duracion_estimacion} onChange={handleChange} required />
          </label>
        </div>
        <div className="form-group">
          <label>Presupuesto Estimado:
            <input name="presupuesto_estimado" type="number" min="1" value={form.presupuesto_estimado} onChange={handleChange} required />
          </label>
        </div>
        <div className="form-group">
          <label>Número de Recursos:
            <input name="numero_recursos" type="number" min="1" value={form.numero_recursos} onChange={handleChange} required />
          </label>
        </div>
        <div className="form-group tecnologias-group-wrapper">
          <label>Tecnologías:</label>
          <div className="tecnologias-group">
            {opciones.tecnologias.map((tec) => (
              <label key={tec}>
                <input
                  type="checkbox"
                  name="tecnologias"
                  value={tec}
                  checked={form.tecnologias.includes(tec)}
                  onChange={handleChange}
                />
                {tec}
              </label>
            ))}
          </div>
        </div>
        <div className="form-group">
          <label>Complejidad:
            <select name="complejidad" value={form.complejidad} onChange={handleChange} required>
              <option value="baja">Baja</option>
              <option value="media">Media</option>
              <option value="alta">Alta</option>
            </select>
          </label>
        </div>
        <div className="form-group">
          <label>Experiencia del Equipo (años):
            <input name="experiencia_equipo" type="number" min="1" value={form.experiencia_equipo} onChange={handleChange} required />
          </label>
        </div>
        <div className="form-group">
          <label>Número de Hitos Clave:
            <input name="hitos_clave" type="number" min="1" value={form.hitos_clave} onChange={handleChange} required />
          </label>
        </div>
        <div className="buttons-row main-actions">
          <button type="button" onClick={handleLimpiarCampos} disabled={loading} className="btn-secondary" title="Limpiar formulario">
            Limpiar Datos
          </button>
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? (
              <span className="flex-center gap-2">
                <div className="mini-spinner"></div>
                Procesando...
              </span>
            ) : 'Generar Predicción'}
          </button>
        </div>
      </form>
      

      <ModalResultadoRiesgoPrincipal
        open={modalRiesgoOpen}
        onClose={() => setModalRiesgoOpen(false)}
        resultado={resultadoRiesgo}
        proyecto={formPrediccion}
      />
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      </main>
    </>
  );
}

export default App;
