import { useEffect, useRef, useState } from 'react'
import { ArrowRight, ChevronDown, Home, Lock, LogOut, Menu, Moon, Sun, Upload as UploadIcon, X } from 'lucide-react'

// Top navigation of the dashboard: logo, grouped menus (a group with one page is a plain link), theme, account.
// The pages themselves come from App.jsx; this file only draws and opens/closes menus.
export const GROUPS = [
  { id: 'insights', label: 'Insights', blurb: 'Read your numbers: totals, patterns and what comes next.', ids: ['overview', 'trends', 'forecast'], tone: 'from-emerald-300 via-teal-200 to-white' },
  { id: 'plan', label: 'Plan', blurb: 'Test changes, find the best mix and audit the energy use.', ids: ['simulation', 'optimization', 'energyaudit', 'factorchange'], tone: 'from-indigo-300 via-violet-200 to-white' },
  { id: 'data', label: 'My data', blurb: 'Bring your own file and keep every analysis.', ids: ['upload', 'history'], tone: 'from-amber-300 via-orange-200 to-white' },
]

export function groupOf(pageId) {
  return GROUPS.find((g) => g.ids.includes(pageId))
}

export default function AppNav({ pages, current, go, loggedIn, dark, setDark, session, profile, authConfigured, onSignOut, demo, showBackToData }) {
  const [openId, setOpenId] = useState(null)       // which group menu is open
  const [sheet, setSheet] = useState(false)        // phone menu
  const bar = useRef(null)

  // Close menus on outside click, Escape and page change.
  useEffect(() => {
    const down = (e) => { if (bar.current && !bar.current.contains(e.target)) setOpenId(null) }
    const key = (e) => { if (e.key === 'Escape') { setOpenId(null); setSheet(false) } }
    document.addEventListener('mousedown', down)
    document.addEventListener('keydown', key)
    return () => { document.removeEventListener('mousedown', down); document.removeEventListener('keydown', key) }
  }, [])
  useEffect(() => { setOpenId(null); setSheet(false) }, [current.id])
  useEffect(() => {
    document.body.style.overflow = sheet ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [sheet])

  const byId = Object.fromEntries(pages.map((p) => [p.id, p]))
  const groups = GROUPS.map((g) => ({ ...g, items: g.ids.map((i) => byId[i]).filter(Boolean) })).filter((g) => g.items.length)
  const activeGroup = groupOf(current.id)?.id

  const item = (p, onPick) => {
    const Icon = p.icon
    const on = current.id === p.id
    return (
      <button key={p.id} role="menuitem" onClick={() => onPick(p.id)}
        className={`group flex w-full items-start gap-3 rounded-xl px-3 py-2.5 text-left transition ${on ? 'bg-white/10' : 'hover:bg-white/[.06]'}`}>
        <span className={`mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg ${on ? 'bg-brand-500 text-slate-950' : 'bg-white/[.07] text-white/70 group-hover:text-white'}`}><Icon size={16} /></span>
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-1.5 text-sm font-semibold text-white">{p.label}{p.locked && !loggedIn && <Lock size={12} className="opacity-60" aria-label="Login required" />}</span>
          <span className="mt-0.5 block text-xs leading-snug text-white/55">{p.desc}</span>
        </span>
      </button>
    )
  }

  return (
    <>
    <header ref={bar} className="app-head sticky top-0 z-40">
      <div className="flex items-center gap-3 px-4 py-3 sm:px-8">
        <a href="#home" className="flex shrink-0 items-center gap-2.5" aria-label="Carbonomics-AI home">
          <img src="./favicon.svg" alt="" className="h-9 w-9" />
          <span className="hidden leading-tight sm:block">
            <span className="block text-[15px] font-semibold text-slate-900 dark:text-white">Carbonomics-AI</span>
            <span className="kicker block !text-[10px]">Carbon intelligence</span>
          </span>
        </a>

        <nav className="mx-auto hidden items-center gap-1 lg:flex" aria-label="Dashboard">
          {groups.map((g) => {
            const single = g.items.length === 1
            const open = openId === g.id
            const here = activeGroup === g.id
            const base = `nav-item inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-[15px] font-medium transition`
            const tone = open ? 'nav-item-open' : here ? 'nav-item-here' : ''
            if (single) {
              const p = g.items[0]
              return <button key={g.id} onClick={() => go(p.id)} className={`${base} ${tone}`}>{p.label}</button>
            }
            return (
              <div key={g.id} className="relative">
                <button onClick={() => setOpenId(open ? null : g.id)} aria-expanded={open} aria-haspopup="menu" className={`${base} ${tone}`}>
                  {g.label} <ChevronDown size={14} className={`transition ${open ? 'rotate-180' : ''}`} />
                </button>
                {open && (
                  <div role="menu" className="nav-pop absolute left-1/2 top-full z-50 mt-3 w-[min(46rem,92vw)] -translate-x-1/2">
                    <span className="nav-pop-arrow" aria-hidden="true" />
                    <div className="grid gap-5 md:grid-cols-[1fr_15rem]">
                      <div>
                        <div className="kicker !text-brand-400 mb-2 px-3">{g.label}</div>
                        <div className="grid gap-0.5 sm:grid-cols-2">{g.items.map((p) => item(p, go))}</div>
                      </div>
                      <div className="hidden md:block">
                        <div className={`h-28 rounded-2xl bg-gradient-to-br ${g.tone} grain`} aria-hidden="true" />
                        <div className="mt-3 text-sm font-semibold text-white">{g.label}</div>
                        <p className="mt-1 text-xs leading-relaxed text-white/55">{g.blurb}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2 lg:ml-0">
          {showBackToData && <a href="#upload" className="btn-ghost hidden xl:inline-flex"><UploadIcon size={14} /> Back to my data</a>}
          <a href="#home" className="btn-ghost hidden xl:inline-flex"><Home size={14} /> Home</a>
          <button onClick={() => setDark(!dark)} aria-label="Toggle dark mode" className="icon-btn">{dark ? <Sun size={17} /> : <Moon size={17} />}</button>
          {authConfigured && (session
            ? (
              <>
                <span className="muted hidden max-w-[12rem] truncate text-xs 2xl:inline" title={session.email}>{profile?.full_name || session.email}</span>
                <button onClick={onSignOut} className="btn-ghost"><LogOut size={14} /> <span className="hidden sm:inline">Log out</span></button>
              </>
            )
            : <a href="#login" className="btn-primary">Log in <ArrowRight size={14} /></a>)}
          <button onClick={() => setSheet(true)} className="icon-btn lg:hidden" aria-label="Open menu"><Menu size={19} /></button>
        </div>
      </div>
    </header>

      {sheet && (
        <div className="app-sheet fixed inset-0 z-50 overflow-y-auto lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <div className="flex items-center justify-between px-4 py-3">
            <span className="flex items-center gap-2.5"><img src="./favicon.svg" alt="" className="h-9 w-9" /><span className="text-[15px] font-semibold text-slate-900 dark:text-white">Carbonomics-AI</span></span>
            <button onClick={() => setSheet(false)} className="icon-btn" aria-label="Close menu"><X size={19} /></button>
          </div>
          <div className="space-y-6 px-4 pb-10 pt-2">
            {groups.map((g) => (
              <section key={g.id}>
                <div className="kicker mb-1.5 px-1">{g.label}</div>
                <div className="space-y-1">
                  {g.items.map((p) => {
                    const Icon = p.icon
                    const on = current.id === p.id
                    return (
                      <button key={p.id} onClick={() => go(p.id)} className={`sheet-row flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left ${on ? 'sheet-row-on' : ''}`}>
                        <Icon size={18} />
                        <span className="min-w-0 flex-1"><span className="block text-[15px] font-semibold">{p.label}</span><span className="block text-xs opacity-60">{p.desc}</span></span>
                        {p.locked && !loggedIn && <Lock size={13} className="opacity-60" aria-label="Login required" />}
                      </button>
                    )
                  })}
                </div>
              </section>
            ))}
            <div className="flex flex-wrap gap-2 border-t border-slate-200 pt-4 dark:border-white/10">
              <a href="#home" className="btn-ghost"><Home size={14} /> Home</a>
              {showBackToData && <a href="#upload" className="btn-ghost"><UploadIcon size={14} /> Back to my data</a>}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
