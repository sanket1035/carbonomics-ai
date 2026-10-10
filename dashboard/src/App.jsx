import { useEffect, useState } from 'react'
import { BarChart3, ClipboardCheck, FlaskConical, Scale, Gauge, History as HistoryIcon, Home, LineChart as LineIcon, LogOut, Lock, Menu, Moon, Sun, Target, Upload as UploadIcon, X } from 'lucide-react'
import { Synthetic, ThemeCtx } from './ui.jsx'
import Overview from './pages/Overview.jsx'
import Trends from './pages/Trends.jsx'
import Forecast from './pages/Forecast.jsx'
import Simulation from './pages/Simulation.jsx'
import Optimization from './pages/Optimization.jsx'
import FactorChange from './pages/FactorChange.jsx'
import EnergyAudit, { MyEnergyAudit } from './pages/EnergyAudit.jsx'
import Upload, { MyForecast, MyOptimization, MyOverview, MySimulation, MyTrends } from './pages/Upload.jsx'
import HistoryPage from './pages/History.jsx'
import Landing from './pages/Landing.jsx'
import Login from './pages/Login.jsx'
import { Privacy, Terms } from './pages/Legal.jsx'
import { authConfigured, signOut, useAuth } from './auth.js'
import { api } from './api.js'

const PAGES = [
  { id: 'overview', label: 'Overview', icon: Gauge, C: Overview, demo: true },
  { id: 'trends', label: 'Trends', icon: LineIcon, C: Trends, demo: true },
  { id: 'forecast', label: 'Forecast', icon: BarChart3, C: Forecast, demo: true },
  { id: 'simulation', label: 'Simulation', icon: FlaskConical, C: Simulation, demo: true },
  { id: 'optimization', label: 'Optimization', icon: Target, C: Optimization, demo: true },
  { id: 'energyaudit', label: 'Energy Audit', icon: ClipboardCheck, C: EnergyAudit, demo: true },
  { id: 'factorchange', label: 'Why it changed', icon: Scale, C: Overview, demo: true, mineOnly: true },
  { id: 'upload', label: 'Upload your data', icon: UploadIcon, C: Upload, locked: true, needsData: false },
  { id: 'history', label: 'History', icon: HistoryIcon, C: HistoryPage, locked: true, needsData: false },
]

const readTheme = () => {
  try {
    const saved = localStorage.getItem('carbonomics-theme')
    if (saved) return saved === 'dark'
  } catch { /* storage may be blocked */ }
  return true   // dark is the default look; the toggle switches to light
}

// '#login?next=upload' -> { route: 'login', next: 'upload' }
const parseHash = () => {
  const [route, query = ''] = location.hash.slice(1).split('?')
  return { route: route || 'home', next: new URLSearchParams(query).get('next') || 'upload' }
}
const goto = (hash) => { location.hash = hash }

// The last analysis survives a page reload (this tab only), so the menu does not empty itself.
const SAVED_KEY = 'carbonomics-last-analysis'
const readSaved = () => {
  try { return JSON.parse(sessionStorage.getItem(SAVED_KEY)) } catch { return null }
}
const writeSaved = (a) => {
  try { sessionStorage.setItem(SAVED_KEY, JSON.stringify(a)) } catch { /* too big or storage blocked: fine */ }
}
// The optimization plan that goes into the PDF report is kept the same way, so a reload does not drop it.
const PLAN_KEY = 'carbonomics-last-plan'
const readPlan = () => {
  try { return JSON.parse(sessionStorage.getItem(PLAN_KEY)) } catch { return null }
}
const writePlan = (p) => {
  try { p ? sessionStorage.setItem(PLAN_KEY, JSON.stringify(p)) : sessionStorage.removeItem(PLAN_KEY) } catch { /* storage blocked: fine */ }
}

export default function App() {
  const [{ route, next }, setRoute] = useState(parseHash)
  const [dark, setDark] = useState(readTheme)
  const { session, profile } = useAuth()

  useEffect(() => {
    const on = () => { setRoute(parseHash()); window.scrollTo(0, 0) }
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    try { localStorage.setItem('carbonomics-theme', dark ? 'dark' : 'light') } catch { /* ignore */ }
  }, [dark])

  // Without Supabase settings (local development) the locked pages stay open; the API still decides what it accepts.
  const loggedIn = Boolean(session) || !authConfigured
  // '#demo/trends' always shows the fake-data demo, even for a logged-in user; plain '#trends' shows their own data.
  const demo = route.startsWith('demo/')
  const pageId = demo ? route.slice(5) : route
  const demoOk = PAGES.some((p) => p.id === pageId && p.demo && !p.mineOnly)
  const isDash = demo ? true : PAGES.some((p) => p.id === pageId)
  const locked = demo ? false : PAGES.find((p) => p.id === pageId)?.locked

  useEffect(() => { if (demo && !demoOk) goto('demo/overview') }, [demo, demoOk])
  useEffect(() => { if (!demo && PAGES.find((p) => p.id === pageId)?.mineOnly && !session) goto(loggedIn ? 'upload' : `login?next=${route}`) }, [demo, pageId, route, session, loggedIn])
  useEffect(() => { if (locked && !loggedIn) goto(`login?next=${route}`) }, [locked, loggedIn, route])
  useEffect(() => { if (route === 'login' && session) goto(next) }, [route, session, next])

  if (route === 'login') return session ? null : <Login next={next} onDone={(n) => goto(n)} />
  if (route === 'privacy') return <Privacy />
  if (route === 'terms') return <Terms />
  if (!isDash) return <Landing />
  if (locked && !loggedIn) return null
  if (demo && !demoOk) return null
  return <Dashboard page={pageId} demo={demo} dark={dark} setDark={setDark} session={session} profile={profile} loggedIn={loggedIn} />
}

function Dashboard({ page, demo, dark, setDark, session, profile, loggedIn }) {
  const [open, setOpen] = useState(false)
  // Desktop sidebar can be closed with the cross and reopened from the header; the choice is remembered in this browser.
  const [collapsed, setCollapsed] = useState(() => { try { return localStorage.getItem('sidebar-collapsed') === '1' } catch { return false } })
  useEffect(() => { try { localStorage.setItem('sidebar-collapsed', collapsed ? '1' : '0') } catch { /* private window: the sidebar still works */ } }, [collapsed])
  const openMenu = () => { if (window.matchMedia('(min-width: 1024px)').matches) setCollapsed((c) => !c); else setOpen(true) }
  const closeMenu = () => { setOpen(false); setCollapsed(true) }
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [analysis, setAnalysis] = useState(readSaved)   // { result, fileName } of the file the user analysed or opened from History
  const [plan, setPlanState] = useState(readPlan)  // optimization inputs, added to the PDF report
  const setPlan = (p) => { setPlanState(p); writePlan(p) }
  const mine = Boolean(session) && !demo                    // logged-in users see their own data, visitors see the fake demo

  useEffect(() => {
    fetch('./data/dashboard.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setData)
      .catch((e) => setError(`Could not load data/dashboard.json (${e.message}). Run python scripts/run_pipeline.py first.`))
  }, [])

  const go = (id) => {
    setOpen(false)
    const p = PAGES.find((x) => x.id === id)
    location.hash = p?.locked && !loggedIn ? `login?next=${id}` : demo && p?.demo ? `demo/${id}` : id
  }
  const current = PAGES.find((p) => p.id === page) ?? PAGES[0]
  const Page = current.C
  const needsData = current.needsData !== false && !mine
  const showResult = (result, fileName) => { setAnalysis({ result, fileName }); setPlan(null); writeSaved({ result, fileName }) }
  // Opening a saved analysis brings back the newest optimization plan saved for it, so the report includes it again.
  const restorePlan = async (runId) => {
    try {
      const runs = await api('/api/runs?limit=200')
      const saved = runs.find((r) => r.kind === 'optimization' && r.parent_run_id === runId && r.input?.measures?.length)
      if (saved) setPlan({ budget_inr: saved.input.budget_inr, measures: saved.input.measures })
    } catch { /* the report simply has no plan until "Find best plan" is run */ }
  }
  const openAnalysis = (run) => {
    const fileName = run.input?.file_name || run.title || ''
    showResult({ ...run.result, input: { ...run.result.input, file_name: fileName }, run: { saved: true, id: run.id, error: null, title: run.title, opened: true } }, fileName)
    restorePlan(run.id)
    go('overview')
  }
  const MINE = { overview: MyOverview, trends: MyTrends, forecast: MyForecast, simulation: MySimulation, optimization: MyOptimization, energyaudit: MyEnergyAudit, factorchange: FactorChange }
  const MyPage = mine ? MINE[current.id] : null

  // Logged-in users get the result pages only once they have a file analysed; visitors get the fake-data demo.
  const visiblePages = mine
    ? [PAGES.find((p) => p.id === 'upload'), ...(analysis ? PAGES.filter((p) => p.demo) : []), PAGES.find((p) => p.id === 'history')]
    : PAGES.filter((p) => !p.mineOnly && !(demo && session && p.locked))
  const nav = (
    <nav className="flex flex-col gap-1">
      {visiblePages.map(({ id, label, icon: Icon, locked }) => (
        <button key={id} onClick={() => go(id)}
          className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${current.id === id ? 'bg-brand-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'}`}>
          <Icon size={18} /> <span className="flex-1 text-left">{label}</span>
          {locked && !loggedIn && <Lock size={13} className="opacity-60" aria-label="Login required" />}
        </button>
      ))}
    </nav>
  )

  return (
    <ThemeCtx.Provider value={{ dark }}>
      <div className={`min-h-screen ${collapsed ? '' : 'lg:grid lg:grid-cols-[250px_1fr]'}`}>
        <aside className={`${open ? 'fixed inset-0 z-40 block overflow-y-auto bg-white p-5 dark:bg-slate-950' : 'hidden'} ${collapsed ? 'lg:hidden' : 'lg:block'} lg:sticky lg:top-0 lg:h-screen lg:overflow-y-auto lg:border-r lg:border-slate-200 lg:bg-white lg:p-5 dark:lg:border-slate-800 dark:lg:bg-slate-950`}>
          <div className="mb-8 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <img src="./favicon.svg" alt="" className="h-9 w-9" />
              <div>
                <div className="font-semibold leading-tight text-slate-900 dark:text-white">Carbonomics-AI</div>
                <div className="muted text-xs">Carbon intelligence</div>
              </div>
            </div>
            <button className="rounded-lg p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800" onClick={closeMenu} aria-label="Close menu" title="Close menu"><X size={22} /></button>
          </div>
          {nav}
          <a href="#home" className="muted mt-4 flex items-center gap-3 px-3 py-2 text-sm hover:underline"><Home size={16} /> Home</a>
          {demo && session && <a href="#upload" className="mt-2 flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium text-brand-600 hover:bg-slate-100 dark:text-brand-300 dark:hover:bg-slate-800"><UploadIcon size={16} /> Back to my data</a>}
          {!mine && <p className="muted mt-8 text-xs leading-relaxed">Demo campus · FAKE data<br />Random numbers, not a real campus</p>}
        </aside>

        <div className="min-w-0">
          <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-slate-200 bg-white/80 px-4 py-3 backdrop-blur sm:px-8 dark:border-slate-800 dark:bg-slate-950/80">
            <div className="flex items-center gap-3">
              <button className={`rounded-lg p-1 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 ${collapsed ? '' : 'lg:hidden'}`} onClick={openMenu} aria-label="Open menu" title="Open menu"><Menu size={22} /></button>
              <h1 className="text-lg font-semibold text-slate-900 dark:text-white">{current.label}</h1>
            </div>
            <div className="flex items-center gap-3">
              {needsData && <span className="hidden sm:inline-flex items-center gap-2 text-xs muted">Demo numbers are <Synthetic /></span>}
              {authConfigured && (session
                ? (
                  <div className="flex items-center gap-2 text-xs">
                    <span className="muted hidden max-w-[14rem] truncate md:inline" title={session.email}>{profile?.full_name || session.email}{profile?.role && profile.role !== 'other' ? ` (${profile.role})` : ''}</span>
                    <button onClick={() => signOut().then(() => { try { sessionStorage.removeItem(SAVED_KEY) } catch { /* ignore */ } location.hash = 'home' })} className="inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-slate-600 ring-1 ring-slate-200 hover:bg-slate-100 dark:text-slate-300 dark:ring-slate-800 dark:hover:bg-slate-800"><LogOut size={15} /> Log out</button>
                  </div>
                )
                : <a href="#login" className="rounded-xl bg-brand-600 px-3 py-2 text-xs font-medium text-white hover:bg-brand-700">Log in</a>)}
              <button onClick={() => setDark(!dark)} aria-label="Toggle dark mode"
                className="rounded-xl p-2 text-slate-600 ring-1 ring-slate-200 hover:bg-slate-100 dark:text-slate-300 dark:ring-slate-800 dark:hover:bg-slate-800">
                {dark ? <Sun size={18} /> : <Moon size={18} />}
              </button>
            </div>
          </header>

          <main key={page} className="page-in mx-auto max-w-7xl px-4 py-6 sm:px-8">
            {needsData && <div className="mb-5 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900 ring-1 ring-amber-200 dark:bg-amber-950 dark:text-amber-200 dark:ring-amber-900"><b>Demo with FAKE data.</b> Every number on this page is random and made up for illustration. It is not from any real campus.</div>}
            {needsData && error && <div className="card text-sm text-rose-600">{error}</div>}
            {needsData && !error && !data && <div className="muted text-sm">Loading…</div>}
            {needsData && data && <Page data={data} />}
            {mine && current.demo && !analysis && <div className="card text-sm">Upload a file first, then the results appear here. <a className="underline" href="#upload">Go to Upload</a></div>}
            {mine && current.demo && analysis && <MyPage a={analysis} plan={plan} onPlan={setPlan} />}
            {!mine && !needsData && <Page />}
            {mine && !current.demo && <Page analysis={analysis} onResult={showResult} onOpenAnalysis={openAnalysis} />}
          </main>
          <footer className="muted px-4 pb-8 text-center text-xs sm:px-8">Carbonomics-AI · final-year project, KKWIEER Nashik · © 2026 Team Carbonomics, all rights reserved · <a className="underline" href="#privacy">Privacy</a> · <a className="underline" href="#terms">Terms</a> {!mine && ' · all numbers in this demo are FAKE, made up for illustration.'}</footer>
        </div>
      </div>
    </ThemeCtx.Provider>
  )
}
