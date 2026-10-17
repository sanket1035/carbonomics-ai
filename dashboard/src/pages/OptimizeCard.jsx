import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Check, Fan, Fuel, Lightbulb, Loader2, Plus, Sparkles, Sun, Trash2 } from 'lucide-react'
import { Badge, COLORS, Callout, Card, Kpi, fmt, useChartTheme } from '../ui.jsx'
import { api } from '../api.js'

const YourInputs = () => <Badge tone="blue">YOUR INPUTS</Badge>
const field = 'w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 dark:border-white/10 dark:bg-black/30'

// 3300000 -> "₹33.00 lakh"; shown next to the budget box so a missing zero is easy to spot.
export function inr(n) {
  if (n == null || Number.isNaN(n)) return '-'
  const v = Math.abs(n)
  if (v >= 1e7) return `₹${fmt(n / 1e7, 2)} crore`
  if (v >= 1e5) return `₹${fmt(n / 1e5, 2)} lakh`
  return `₹${fmt(n)}`
}

let nextId = 1
const blank = (mode = 'plain', label = '', acts_on = 'electricity') => ({ id: nextId++, mode, label, acts_on, pct: false, saving: '', kwp: '', yield_: '', capex: '', units: '1', ann: '', group: '' })

// Starting points only: they set the name and what is reduced. Every number is typed by the user.
const TEMPLATES = [
  { key: 'solar', title: 'Solar panels', hint: 'Cuts bought electricity', icon: Sun, make: () => blank('solar', 'Rooftop solar'), needs: 'electricity' },
  { key: 'led', title: 'Efficient lighting', hint: 'LED, better fans', icon: Lightbulb, make: () => blank('plain', 'Efficient lighting'), needs: 'electricity' },
  { key: 'ac', title: 'Efficient AC and motors', hint: 'Less electricity per hour', icon: Fan, make: () => blank('plain', 'Efficient AC and motors'), needs: 'electricity' },
  { key: 'dg', title: 'Use the generator less', hint: 'Cuts diesel litres', icon: Fuel, make: () => blank('plain', 'Less generator use', 'diesel'), needs: 'diesel' },
  { key: 'other', title: 'Something else', hint: 'Your own measure', icon: Plus, make: () => blank() },
]

const missing = (m) => {
  const out = []
  if (!m.label.trim()) out.push('a name')
  if (m.mode === 'solar') { if (m.kwp === '' || m.yield_ === '') out.push('panel size and yearly output') } else if (m.saving === '') out.push('the saving')
  if (m.capex === '') out.push('the cost of one unit')
  if (m.units === '' || Number(m.units) < 1) out.push('how many units are possible')
  return out
}

const toBody = (m) => {
  const solar = m.mode === 'solar'
  return {
    label: m.label, acts_on: solar ? 'electricity' : m.acts_on,
    saving_type: solar ? 'fixed_kwh_per_year' : m.pct ? 'pct_of_activity' : m.acts_on === 'electricity' ? 'fixed_kwh_per_year' : 'fixed_litres_per_year',
    saving_value: solar ? Number(m.kwp) * Number(m.yield_) : m.saving === '' ? null : Number(m.saving),
    capex_inr: m.capex === '' ? null : Number(m.capex), max_units: m.units === '' ? null : Number(m.units),
    exclusive_group: m.group || null, annual_saving_inr: m.ann === '' ? null : Number(m.ann),
  }
}

export default function OptimizeCard({ r, onPlan }) {
  const { accounting, input } = r
  const [budget, setBudget] = useState('')
  const [rows, setRows] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [res, setRes] = useState(null)
  const [saveState, setSaveState] = useState(null)

  const hasElec = 'electricity_kwh' in accounting.periods[0]
  const hasDiesel = 'diesel_litres' in accounting.periods[0]
  const upd = (id, k) => (e) => setRows((rs) => rs.map((m) => (m.id === id ? { ...m, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value } : m)))
  const request = (extra = {}) => ({
    periods: accounting.periods.map((p) => ({ period_start: p.period_start, electricity_kwh: p.electricity_kwh, diesel_litres: p.diesel_litres })),
    granularity: input.granularity_analysed, budget_inr: budget === '' ? null : Number(budget),
    measures: rows.map(toBody), ...extra,
  })

  const run = async () => {
    setBusy(true); setError(''); setSaveState(null)
    try {
      const req = request()
      setRes(await api('/api/optimize', { method: 'POST', json: req }))
      onPlan?.({ budget_inr: req.budget_inr, measures: req.measures })
    } catch (e) { setError(e.message); setRes(null); onPlan?.(null) } finally { setBusy(false) }
  }
  const save = async () => {
    setSaveState('saving')
    try {
      const out = await api('/api/optimize', { method: 'POST', json: request({ save: true, title: `Optimization, budget ${inr(Number(budget))}`, parent_run_id: r.run?.id ?? null }) })
      setSaveState(out.run?.saved ? { ok: true, message: 'Plan saved to your history.' } : { ok: false, message: out.run?.error || 'History is not available, so the plan was not saved.' })
    } catch (e) { setSaveState({ ok: false, message: e.message }) }
  }

  const problems = [
    ...(budget === '' || Number(budget) <= 0 ? ['your budget'] : []),
    ...(rows.length === 0 ? ['at least one measure'] : []),
    ...rows.flatMap((m, i) => missing(m).map((x) => `Measure ${i + 1}: ${x}`)),
  ]
  const ready = problems.length === 0
  const add = (t) => setRows((rs) => (rs.length >= 30 ? rs : [...rs, t.make()]))
  const stepHead = (n, title, text, done) => (
    <div className="mb-3 flex items-start gap-3">
      <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${done ? 'bg-emerald-500 text-white' : 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'}`}>{done ? <Check size={14} /> : n}</span>
      <div><div className="font-medium text-slate-900 dark:text-white">{title}</div><div className="muted text-xs">{text}</div></div>
    </div>
  )

  return (
    <div className="space-y-5">
      <Callout tone="blue" title="How this works">
        Tell us how much money you have and which ideas you are considering, with the cost and saving of each. We then pick the mix that cuts the most emissions within your budget.
        Nothing is pre-filled: the answer is only as good as the figures you type.
      </Callout>

      <Card badge={<YourInputs />}>
        {stepHead(1, 'Your budget', 'The most you can spend in total.', budget !== '' && Number(budget) > 0)}
        <label className="block max-w-sm text-sm">
          <input type="number" min="0" className={field} value={budget} onChange={(e) => setBudget(e.target.value)} placeholder="e.g. 3300000" aria-label="Total budget in rupees" />
          <span className="muted mt-1.5 block text-xs">{budget !== '' && Number(budget) >= 0 ? `That is ${inr(Number(budget))}.` : 'In rupees (₹).'}</span>
        </label>
      </Card>

      <Card>
        {stepHead(2, 'Your ideas', 'Pick a starting point, then fill in its numbers. Add as many as you like.', rows.length > 0 && rows.every((m) => missing(m).length === 0))}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {TEMPLATES.filter((t) => t.key === 'other' || (t.needs === 'electricity' ? hasElec : hasDiesel)).map((t) => (
            <button key={t.key} onClick={() => add(t)} disabled={rows.length >= 30}
              className="group flex flex-col items-start gap-1 rounded-2xl border border-slate-200 p-3 text-left transition hover:-translate-y-0.5 hover:border-emerald-500/60 hover:bg-emerald-500/5 dark:border-white/10">
              <t.icon size={20} className="text-emerald-600 transition group-hover:scale-110 dark:text-emerald-300" />
              <span className="text-sm font-medium text-slate-900 dark:text-white">{t.title}</span>
              <span className="muted text-xs">{t.hint}</span>
            </button>
          ))}
        </div>

        <div className="mt-4 space-y-3">
          {rows.map((m, i) => (
            <div key={m.id} className="rise rounded-2xl border border-slate-200 bg-slate-50/60 p-4 dark:border-white/10 dark:bg-white/[.02]">
              <div className="mb-3 flex items-center justify-between gap-3">
                <input className={`${field} max-w-xs font-medium`} maxLength={100} value={m.label} onChange={upd(m.id, 'label')} placeholder="Name of this idea" aria-label={`Name of idea ${i + 1}`} />
                <button onClick={() => setRows((rs) => rs.filter((x) => x.id !== m.id))} aria-label={`Remove idea ${i + 1}`} className="rounded-lg p-2 text-rose-500 hover:bg-rose-500/10"><Trash2 size={16} /></button>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                {m.mode === 'plain' ? (
                  <>
                    <label className="text-sm"><span className="muted mb-1 block text-xs">What does it reduce?</span>
                      <select className={field} value={m.acts_on} onChange={upd(m.id, 'acts_on')}>
                        {hasElec && <option value="electricity">Electricity</option>}
                        {hasDiesel && <option value="diesel">Generator diesel</option>}
                      </select></label>
                    <label className="text-sm"><span className="muted mb-1 block text-xs">{m.pct ? 'Saving, % of yearly use' : `Saving per unit (${m.acts_on === 'electricity' ? 'kWh' : 'litres'} a year)`}</span>
                      <input type="number" min="0" className={field} value={m.saving} onChange={upd(m.id, 'saving')} />
                      <span className="mt-1.5 flex items-center gap-1.5 text-xs"><input type="checkbox" checked={m.pct} onChange={upd(m.id, 'pct')} /> I know it as a percentage</span></label>
                  </>
                ) : (
                  <>
                    <label className="text-sm"><span className="muted mb-1 block text-xs">Panel size of one unit (kWp)</span>
                      <input type="number" min="0" className={field} value={m.kwp} onChange={upd(m.id, 'kwp')} /></label>
                    <label className="text-sm"><span className="muted mb-1 block text-xs">Yearly output per kWp (kWh), your figure</span>
                      <input type="number" min="0" className={field} value={m.yield_} onChange={upd(m.id, 'yield_')} /></label>
                  </>
                )}
                <label className="text-sm"><span className="muted mb-1 block text-xs">Cost of one unit (₹)</span>
                  <input type="number" min="0" className={field} value={m.capex} onChange={upd(m.id, 'capex')} /></label>
                <label className="text-sm"><span className="muted mb-1 block text-xs">How many units are possible?</span>
                  <input type="number" min="1" max="1000" className={field} value={m.units} onChange={upd(m.id, 'units')} /></label>
              </div>
              <details className="mt-3 text-sm">
                <summary className="muted cursor-pointer text-xs">More options (payback, either-or)</summary>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <label className="text-sm"><span className="muted mb-1 block text-xs">Rupees saved per unit each year (to work out payback)</span>
                    <input type="number" min="0" className={field} value={m.ann} onChange={upd(m.id, 'ann')} /></label>
                  <label className="text-sm"><span className="muted mb-1 block text-xs">Either-or group: ideas with the same word, pick only one</span>
                    <input className={field} maxLength={40} value={m.group} onChange={upd(m.id, 'group')} placeholder="e.g. lighting" /></label>
                </div>
              </details>
            </div>
          ))}
          {rows.length === 0 && <p className="muted rounded-2xl border border-dashed border-slate-300 p-4 text-center text-sm dark:border-white/15">No ideas yet. Pick one above to start.</p>}
        </div>
      </Card>

      <Card>
        {stepHead(3, 'Find the best mix', ready ? 'Everything is filled in.' : `Still needed: ${problems.slice(0, 3).join('; ')}${problems.length > 3 ? ` and ${problems.length - 3} more` : ''}.`, ready)}
        <button onClick={run} disabled={busy || !ready}
          className="inline-flex items-center gap-2 rounded-full bg-brand-600 px-6 py-2.5 text-sm font-medium text-white shadow-lg shadow-teal-900/30 transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40">
          {busy ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />} {busy ? 'Working it out…' : 'Find best plan'}
        </button>
        {error && <p role="alert" className="mt-3 text-sm text-rose-500">{error}</p>}
      </Card>

      {res && (
        <Card title="Your plan" subtitle="The mix that cuts the most within your budget.">
          <PlanView r={res} />
          <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-slate-200 pt-4 dark:border-white/10">
            <button onClick={save} disabled={saveState === 'saving'}
              className="inline-flex items-center gap-2 rounded-full bg-brand-600 px-5 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-50">
              {saveState === 'saving' && <Loader2 size={16} className="animate-spin" />} Save this plan
            </button>
            {saveState && saveState !== 'saving' && <span className={`text-xs ${saveState.ok ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500'}`}>{saveState.message}</span>}
          </div>
        </Card>
      )}
    </div>
  )
}

const th = 'py-2 pr-4 text-left text-xs font-medium uppercase tracking-wide'

// The result of /api/optimize. Also used by the History page to show a saved plan.
export function PlanView({ r }) {
  const t = useChartTheme()
  const { baseline, optimal: o, greedy: g, ranking } = r
  const chart = ranking.map((x) => ({ name: x.label, pct: x.pct_of_baseline_per_unit }))
  const names = o.selected.map((x) => `${x.label}${x.units > 1 ? ` x${x.units}` : ''}`).join(', ')
  return (
    <div className="space-y-5">
      <p className="rounded-2xl border border-emerald-500/30 bg-emerald-500/5 p-4 text-sm leading-relaxed text-slate-800 dark:text-slate-100">
        {o.selected.length === 0
          ? `Nothing fits a budget of ${inr(r.budget_inr)} yet.`
          : `Spend ${inr(o.total_capex_inr)} of your ${inr(r.budget_inr)} on ${names}. This saves about ${fmt(o.tco2e_saved, 1)} tCO₂e a year, ${fmt(o.pct_of_baseline, 1)}% of your current ${fmt(baseline.tco2e_per_year, 1)}.`}
      </p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Baseline" value={fmt(baseline.tco2e_per_year, 1)} unit="tCO₂e / year" sub={`from ${baseline.days_covered} days of your data`} />
        <Kpi label="Best plan saves" value={fmt(o.tco2e_saved, 1)} unit="tCO₂e / year" sub={`${fmt(o.pct_of_baseline, 1)}% of baseline`} />
        <Kpi label="Plan cost" value={inr(o.total_capex_inr)} sub={`budget ${inr(r.budget_inr)}`} />
        <Kpi label="Payback" value={o.payback_years != null ? fmt(o.payback_years, 1) : '-'} unit={o.payback_years != null ? 'years' : ''} sub={o.payback_years != null ? 'from your rupee savings' : 'needs a yearly ₹ saving for every chosen measure'} />
      </div>

      {o.selected.length === 0
        ? <Callout tone="blue">No measure fits this budget. Increase the budget or lower a measure's cost.</Callout>
        : (
          <div className="overflow-x-auto">
            <h4 className="mb-2 text-sm font-semibold text-slate-900 dark:text-slate-100">Recommended plan (selected by the optimiser)</h4>
            <table className="w-full text-sm">
              <thead><tr className="muted border-b border-slate-200 dark:border-slate-800"><th className={th}>Measure</th><th className={`${th} text-right`}>Units</th><th className={`${th} text-right`}>Cost</th><th className={`${th} text-right`}>tCO₂e saved / year</th><th className={`${th} text-right`}>% of baseline</th></tr></thead>
              <tbody>
                {o.selected.map((s) => (
                  <tr key={s.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800/60">
                    <td className="py-2.5 pr-4 font-medium">{s.label}</td><td className="py-2.5 pr-4 text-right tabular-nums">{s.units}</td>
                    <td className="py-2.5 pr-4 text-right tabular-nums">{inr(s.capex_inr)}</td><td className="py-2.5 pr-4 text-right tabular-nums">{fmt(s.tco2e_saved, 2)}</td><td className="py-2.5 text-right tabular-nums">{fmt(s.pct_of_baseline, 1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

      <details className="rounded-2xl border border-slate-200 p-4 dark:border-white/10">
      <summary className="cursor-pointer text-sm font-medium text-slate-900 dark:text-slate-100">See every idea compared, and the checks behind the plan</summary>
      <div className="mt-4 space-y-5">
      <div className="overflow-x-auto">
        <h4 className="mb-2 text-sm font-semibold text-slate-900 dark:text-slate-100">Each measure on its own, best reduction first</h4>
        <table className="w-full text-sm">
          <thead><tr className="muted border-b border-slate-200 dark:border-slate-800"><th className={th}>#</th><th className={th}>Measure</th><th className={`${th} text-right`}>% reduction (one unit)</th><th className={`${th} text-right`}>₹ per tCO₂e saved</th><th className={`${th} text-right`}>Payback (years)</th></tr></thead>
          <tbody>
            {ranking.map((x, i) => (
              <tr key={x.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800/60">
                <td className="py-2.5 pr-4">{i + 1}</td>
                <td className="py-2.5 pr-4 font-medium">{x.label} {i === 0 && <Badge tone="green">largest reduction</Badge>} {x.cap_applied && <Badge tone="amber">capped at the source's use</Badge>}</td>
                <td className="py-2.5 pr-4 text-right tabular-nums">{fmt(x.pct_of_baseline_per_unit, 2)}%</td>
                <td className="py-2.5 pr-4 text-right tabular-nums">{x.inr_per_tco2e != null ? inr(x.inr_per_tco2e) : '-'}</td>
                <td className="py-2.5 text-right tabular-nums">{x.payback_years != null ? fmt(x.payback_years, 1) : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="h-56">
        <ResponsiveContainer>
          <BarChart data={chart} layout="vertical" margin={{ left: 10, right: 20 }}>
            <CartesianGrid stroke={t.grid} horizontal={false} />
            <XAxis type="number" stroke={t.axis} tickLine={false} tickFormatter={(v) => `${v}%`} />
            <YAxis type="category" dataKey="name" stroke={t.axis} tickLine={false} width={150} />
            <Tooltip contentStyle={t.tip} formatter={(v) => [`${fmt(v, 2)}% of baseline`, 'Reduction (one unit)']} />
            <Bar animationDuration={900} dataKey="pct" fill={COLORS.electricity} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <p className="muted text-xs">
        Comparison: ordering measures by cost-effectiveness alone (a simple "cheapest first" rule) would save {fmt(g.tco2e_saved, 1)} tCO₂e per year for {inr(g.total_capex_inr)};
        the optimiser's plan saves {fmt(o.tco2e_saved, 1)}. Solver: {r.solver_status}; cross-check against the scenario calculation {r.consistency_check.passed ? 'passed' : 'FAILED'}.
      </p>
      </div>
      </details>
      {r.notes.map((n) => <Callout key={n} tone="blue">{n}</Callout>)}
      <p className="muted text-xs">{r.disclaimer}</p>
    </div>
  )
}
