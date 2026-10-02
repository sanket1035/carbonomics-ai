import { useEffect, useState } from 'react'
import { BarChart3, Gauge, LineChart as LineIcon, ListChecks, Menu, Moon, ShieldCheck, Sun, X } from 'lucide-react'
import { Synthetic, ThemeCtx } from './ui.jsx'
import Overview from './pages/Overview.jsx'
import Trends from './pages/Trends.jsx'
import Forecast from './pages/Forecast.jsx'
import Factors from './pages/Factors.jsx'
import Quality from './pages/Quality.jsx'

const PAGES = [
  { id: 'overview', label: 'Overview', icon: Gauge, C: Overview },
  { id: 'trends', label: 'Trends', icon: LineIcon, C: Trends },
  { id: 'forecast', label: 'Forecast', icon: BarChart3, C: Forecast },
  { id: 'factors', label: 'Emission factors', icon: ListChecks, C: Factors },
  { id: 'quality', label: 'Data & QA', icon: ShieldCheck, C: Quality },
]

const readTheme = () => {
  try {
    const saved = localStorage.getItem('carbonomics-theme')
    if (saved) return saved === 'dark'
  } catch { /* storage may be blocked */ }
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
}

export default function App() {
  const [page, setPage] = useState(() => (location.hash.slice(1) || 'overview'))
  const [dark, setDark] = useState(readTheme)
  const [open, setOpen] = useState(false)
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    try { localStorage.setItem('carbonomics-theme', dark ? 'dark' : 'light') } catch { /* ignore */ }
  }, [dark])

  useEffect(() => {
    fetch('./data/dashboard.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setData)
      .catch((e) => setError(`Could not load data/dashboard.json (${e.message}). Run python scripts/run_pipeline.py first.`))
  }, [])

  const go = (id) => { setPage(id); location.hash = id; setOpen(false) }
  const current = PAGES.find((p) => p.id === page) ?? PAGES[0]
  const Page = current.C

  const nav = (
    <nav className="flex flex-col gap-1">
      {PAGES.map(({ id, label, icon: Icon }) => (
        <button key={id} onClick={() => go(id)}
          className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${current.id === id ? 'bg-brand-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'}`}>
          <Icon size={18} /> {label}
        </button>
      ))}
    </nav>
  )

  return (
    <ThemeCtx.Provider value={{ dark }}>
      <div className="min-h-screen lg:grid lg:grid-cols-[250px_1fr]">
        <aside className={`${open ? 'fixed inset-0 z-40 block bg-white p-5 dark:bg-slate-950' : 'hidden'} lg:static lg:block lg:border-r lg:border-slate-200 lg:bg-white lg:p-5 dark:lg:border-slate-800 dark:lg:bg-slate-950`}>
          <div className="mb-8 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <img src="./favicon.svg" alt="" className="h-9 w-9" />
              <div>
                <div className="font-semibold leading-tight text-slate-900 dark:text-white">Carbonomics-AI</div>
                <div className="muted text-xs">Carbon intelligence</div>
              </div>
            </div>
            <button className="lg:hidden" onClick={() => setOpen(false)} aria-label="Close menu"><X size={22} /></button>
          </div>
          {nav}
          <p className="muted mt-8 text-xs leading-relaxed">K. K. Wagh Panchvati Campus, Nashik<br />Calendar year 2025</p>
        </aside>

        <div className="min-w-0">
          <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-slate-200 bg-white/80 px-4 py-3 backdrop-blur sm:px-8 dark:border-slate-800 dark:bg-slate-950/80">
            <div className="flex items-center gap-3">
              <button className="lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu"><Menu size={22} /></button>
              <h1 className="text-lg font-semibold text-slate-900 dark:text-white">{current.label}</h1>
            </div>
            <div className="flex items-center gap-3">
              <span className="hidden sm:inline-flex items-center gap-2 text-xs muted">Weekly data is <Synthetic /></span>
              <button onClick={() => setDark(!dark)} aria-label="Toggle dark mode"
                className="rounded-xl p-2 text-slate-600 ring-1 ring-slate-200 hover:bg-slate-100 dark:text-slate-300 dark:ring-slate-800 dark:hover:bg-slate-800">
                {dark ? <Sun size={18} /> : <Moon size={18} />}
              </button>
            </div>
          </header>

          <main className="mx-auto max-w-7xl px-4 py-6 sm:px-8">
            {error && <div className="card text-sm text-rose-600">{error}</div>}
            {!error && !data && <div className="muted text-sm">Loading…</div>}
            {data && <Page data={data} />}
          </main>
          <footer className="muted px-4 pb-8 text-center text-xs sm:px-8">Carbonomics-AI · final-year project, KKWIEER Nashik · figures labelled REAL come from the Energy team's monthly log; SYNTHETIC figures are not measurements.</footer>
        </div>
      </div>
    </ThemeCtx.Provider>
  )
}
