import { useEffect, useState } from 'react'
import { BarChart3, ClipboardCheck, FlaskConical, Scale, Gauge, History as HistoryIcon, LineChart as LineIcon, Target, Upload as UploadIcon } from 'lucide-react'
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
import AppNav, { groupOf } from './AppNav.jsx'

const PAGES = [
  { id: 'overview', label: 'Overview', icon: Gauge, C: Overview, demo: true, desc: 'Totals, scopes and sources', blurb: 'Where the emissions come from, in one view.' },
  { id: 'trends', label: 'Trends', icon: LineIcon, C: Trends, demo: true, desc: 'Weekly and monthly patterns', blurb: 'How electricity, diesel and emissions move over time.' },
  { id: 'forecast', label: 'Forecast', icon: BarChart3, C: Forecast, demo: true, desc: 'Next weeks against a naive guess', blurb: 'The next weeks of use, compared honestly with a naive guess.' },
  { id: 'simulation', label: 'Simulation', icon: FlaskConical, C: Simulation, demo: true, desc: 'What-if on electricity and diesel', blurb: 'Change electricity or diesel use and see what it does to emissions.' },
  { id: 'optimization', label: 'Optimization', icon: Target, C: Optimization, demo: true, desc: 'Best mix within a budget', blurb: 'Pick the mix of measures that cuts the most within your budget.' },
  { id: 'energyaudit', label: 'Energy Audit', icon: ClipboardCheck, C: EnergyAudit, demo: true, desc: 'kWh per m² and saving ideas', blurb: 'Electricity per square metre against benchmarks, and where savings could come from.' },
  { id: 'factorchange', label: 'Why it changed', icon: Scale, C: Overview, demo: true, mineOnly: true, desc: 'Use effect vs emission-factor effect', blurb: 'Split a change in emissions into less use and a cleaner grid.' },
  { id: 'upload', label: 'Upload your data', icon: UploadIcon, C: Upload, locked: true, needsData: false, desc: 'CSV or Excel, analysed in seconds', blurb: 'Analyse your own CSV or Excel file.' },
  { id: 'history', label: 'History', icon: HistoryIcon, C: HistoryPage, locked: true, needsData: false, desc: 'Saved analyses and plans', blurb: 'Every analysis and plan you saved, ready to reopen.' },
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
  // '#demo/trends' always shows the sample-data demo, even for a logged-in user; plain '#trends' shows their own data.
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
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [analysis, setAnalysis] = useState(readSaved)   // { result, fileName } of the file the user analysed or opened from History
  const [plan, setPlanState] = useState(readPlan)  // optimization inputs, added to the PDF report
  const setPlan = (p) => { setPlanState(p); writePlan(p) }
  const mine = Boolean(session) && !demo                    // logged-in users see their own data, visitors see the sample demo

  useEffect(() => {
    fetch('./data/dashboard.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setData)
      .catch((e) => setError(`Could not load data/dashboard.json (${e.message}). Run python scripts/run_pipeline.py first.`))
  }, [])

  const go = (id) => {
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

  // Logged-in users get the result pages only once they have a file analysed; visitors get the sample-data demo.
  const visiblePages = mine
    ? [PAGES.find((p) => p.id === 'upload'), ...(analysis ? PAGES.filter((p) => p.demo) : []), PAGES.find((p) => p.id === 'history')]
    : PAGES.filter((p) => !p.mineOnly && !(demo && session && p.locked))
  const group = groupOf(current.id)
  const signOutNow = () => signOut().then(() => { try { sessionStorage.removeItem(SAVED_KEY) } catch { /* ignore */ } location.hash = 'home' })

  return (
    <ThemeCtx.Provider value={{ dark }}>
      <div className="app-shell min-h-screen">
        <div className="app-frame mx-auto flex min-h-screen max-w-[1320px] flex-col">
          <AppNav pages={visiblePages} current={current} go={go} loggedIn={loggedIn} dark={dark} setDark={setDark}
            session={session} profile={profile} authConfigured={authConfigured} onSignOut={signOutNow} demo={demo} showBackToData={demo && Boolean(session)} />

          <div className="frame-rule" aria-hidden="true"><i /><i /></div>

          <div className="mx-auto w-full max-w-[1200px] flex-1 px-4 sm:px-8">
            <div className="page-head page-in flex flex-wrap items-end justify-between gap-4 pb-6 pt-8 sm:pt-12">
              <div className="min-w-0">
                <div className="kicker">{group ? `${group.label} / ` : ''}{current.label}</div>
                <h1 className="mt-2 text-4xl leading-[1.05] text-slate-900 sm:text-5xl dark:text-white">{current.label}</h1>
                <p className="muted mt-3 max-w-2xl text-[15px] leading-relaxed">{current.blurb}</p>
              </div>
              {needsData && <span className="chip-demo">Demo numbers are <Synthetic /></span>}
            </div>

            <main key={page} className="page-in space-y-6 pb-14">
              {needsData && <div className="demo-note"><b>Demo with SAMPLE data.</b> Every number on this page is random and made up for illustration. It is not from any real campus.</div>}
              {needsData && error && <div className="card text-sm text-rose-600">{error}</div>}
              {needsData && !error && !data && <div className="muted text-sm">Loading…</div>}
              {needsData && data && <Page data={data} />}
              {mine && current.demo && !analysis && <div className="card text-sm">Upload a file first, then the results appear here. <a className="underline" href="#upload">Go to Upload</a></div>}
              {mine && current.demo && analysis && <MyPage a={analysis} plan={plan} onPlan={setPlan} />}
              {!mine && !needsData && <Page />}
              {mine && !current.demo && <Page analysis={analysis} onResult={showResult} onOpenAnalysis={openAnalysis} />}
            </main>
          </div>

          <footer className="app-foot px-4 py-6 text-center sm:px-8">
            Carbonomics-AI · final-year project, KKWIEER Nashik · © 2026 Team Carbonomics, all rights reserved · <a className="underline" href="#privacy">Privacy</a> · <a className="underline" href="#terms">Terms</a>{!mine && ' · all numbers in this demo are SAMPLE, made up for illustration.'}
          </footer>
        </div>
      </div>
    </ThemeCtx.Provider>
  )
}
