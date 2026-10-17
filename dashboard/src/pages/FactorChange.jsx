import { useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ArrowRight, Leaf, Zap } from 'lucide-react'
import { api } from '../api.js'
import { Callout, Card, Kpi, fmt, useChartTheme } from '../ui.jsx'

const field = 'w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900'
const GREEN = '#059669', RED = '#e11d48', BASE = '#10b981'

// Default grid version for a calendar year: the fiscal year that ends in it (2025 -> 2024-25), else the closest listed.
const defaultFy = (year, versions) => {
  const ending = versions.find((v) => Number(v.fy.slice(0, 4)) + 1 === year)
  if (ending) return ending.fy
  return versions.reduce((best, v) => (Math.abs(Number(v.fy.slice(0, 4)) + 1 - year) < Math.abs(Number(best.fy.slice(0, 4)) + 1 - year) ? v : best)).fy
}

function Effects({ res }) {
  const t = useChartTheme()
  const { activity_effect_t: act, factor_effect_t: fac, change_t: net } = res.totals
  const rows = [
    { name: 'Your energy use', v: act, fill: act > 0 ? RED : GREEN },
    { name: 'The grid factor', v: fac, fill: fac > 0 ? RED : GREEN },
    { name: 'Net change', v: net, fill: BASE },
  ]
  return (
    <div className="h-64">
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ left: -5 }}>
          <CartesianGrid stroke={t.grid} vertical={false} />
          <XAxis dataKey="name" stroke={t.axis} tickLine={false} />
          <YAxis stroke={t.axis} tickLine={false} axisLine={false} tickFormatter={(v) => fmt(v)} width={60} />
          <ReferenceLine y={0} stroke={t.axis} />
          <Tooltip cursor={false} contentStyle={t.tip} formatter={(v) => [`${v > 0 ? '+' : ''}${fmt(v, 1)} tCO2e`, 'Effect']} />
          <Bar dataKey="v" isAnimationActive={false}>
            {rows.map((r) => <Cell key={r.name} fill={r.fill} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function FactorChange({ a }) {
  const periods = useMemo(() => a.result.accounting.periods?.map((p) => ({ period_start: p.period_start, electricity_kwh: p.electricity_kwh, diesel_litres: p.diesel_litres })), [a])
  const [meta, setMeta] = useState(null)
  const [pick, setPick] = useState(null)
  const [res, setRes] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    if (!periods) return
    api('/api/factor-change', { method: 'POST', json: { periods } }).then((m) => {
      setMeta(m)
      if (m.years.length >= 2) {
        const [ya, yb] = m.years.slice(-2)
        setPick({ ya, yb, fa: defaultFy(ya, m.versions), fb: defaultFy(yb, m.versions) })
      }
    }).catch((e) => setErr(e.message))
  }, [periods])

  useEffect(() => {
    if (!pick || pick.ya === pick.yb) { setRes(null); return }
    setErr('')
    api('/api/factor-change', { method: 'POST', json: { periods, year_a: pick.ya, year_b: pick.yb, fy_a: pick.fa, fy_b: pick.fb } })
      .then(setRes).catch((e) => { setRes(null); setErr(e.message) })
  }, [pick, periods])

  if (!periods) return <Callout tone="blue" title="Per-period detail not available">This run was opened from your history as a summary only. Upload the file again to see why your emissions changed.</Callout>
  if (err && !meta) return <Callout title="Could not load">{err}</Callout>
  if (!meta) return <div className="muted text-sm">Loading…</div>
  if (meta.years.length < 2) return <Callout tone="blue" title="Two full years needed">To compare years, your file needs at least two complete calendar years of data. Yours has {meta.years.length ? `only ${meta.years[0]}` : 'no complete year'}.</Callout>

  const set = (k) => (e) => setPick({ ...pick, [k]: k[0] === 'y' ? Number(e.target.value) : e.target.value })
  const fyOptions = meta.versions.map((v) => <option key={v.fy} value={v.fy}>FY {v.fy} · {v.factor} {v.unit}</option>)
  const yearOptions = meta.years.map((y) => <option key={y} value={y}>{y}</option>)
  const tot = res?.totals
  const good = (x) => x <= 0

  return (
    <div className="space-y-6">
      <Callout tone="blue" title="Why did my emissions change?">
        Emissions = how much energy you use x how polluting each unit is. The second part, the grid factor, changes every year as India adds more clean power,
        and you cannot control it. This page separates the two, so you can see what is your doing and what is the grid's.
      </Callout>

      <Card title="Pick two years to compare" subtitle="The grid factors below are documented values from the app's own list (CEA). You only choose which one to use.">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <label className="muted text-xs">Earlier year</label>
            <select className={field} value={pick.ya} onChange={set('ya')}>{yearOptions}</select>
            <label className="muted text-xs">Grid factor to use for it</label>
            <select className={field} value={pick.fa} onChange={set('fa')}>{fyOptions}</select>
          </div>
          <div className="space-y-2">
            <label className="muted text-xs">Later year</label>
            <select className={field} value={pick.yb} onChange={set('yb')}>{yearOptions}</select>
            <label className="muted text-xs">Grid factor to use for it</label>
            <select className={field} value={pick.fb} onChange={set('fb')}>{fyOptions}</select>
          </div>
        </div>
        {err && <p className="mt-3 text-sm text-rose-600">{err}</p>}
      </Card>

      {res && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <Kpi label={`${res.year_a} to ${res.year_b}`} value={`${tot.change_t > 0 ? '+' : ''}${fmt(tot.change_t, 1)}`} unit="tCO2e" sub={`${fmt(tot.emission_a_t, 1)} to ${fmt(tot.emission_b_t, 1)} tCO2e`} icon={ArrowRight} />
            <Kpi label="Because of your energy use" value={`${tot.activity_effect_t > 0 ? '+' : ''}${fmt(tot.activity_effect_t, 1)}`} unit="tCO2e" sub={good(tot.activity_effect_t) ? 'You used less' : 'You used more'} icon={Zap} />
            <Kpi label="Because of the grid" value={`${tot.factor_effect_t > 0 ? '+' : ''}${fmt(tot.factor_effect_t, 1)}`} unit="tCO2e" sub={good(tot.factor_effect_t) ? 'Grid got cleaner' : 'Grid got dirtier'} icon={Leaf} />
          </div>

          <Card title="In simple words" subtitle="Green bars lower emissions (tCO2e), red bars raise them.">
            <ul className="mb-4 space-y-1.5 text-sm">{res.sentences.map((s) => <li key={s}>{s}</li>)}</ul>
            <Effects res={res} />
          </Card>

          <Card title="Details" subtitle={`Grid factor used: ${res.grid_factor_a} (FY ${res.fy_a}) then ${res.grid_factor_b} (FY ${res.fy_b}) ${res.grid_factor_unit}`}>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="muted border-b border-slate-200 text-left text-xs uppercase tracking-wide dark:border-slate-800">
                  <th className="py-2 pr-4">Source</th><th className="py-2 pr-4 text-right">{res.year_a} use</th><th className="py-2 pr-4 text-right">{res.year_b} use</th>
                  <th className="py-2 pr-4 text-right">Energy-use effect (t)</th><th className="py-2 pr-4 text-right">Grid effect (t)</th><th className="py-2 text-right">Change (t)</th>
                </tr></thead>
                <tbody>
                  {res.rows.map((r) => (
                    <tr key={r.source} className="border-b border-slate-100 last:border-0 dark:border-slate-800/60">
                      <td className="py-2.5 pr-4 font-medium">{r.label}</td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">{fmt(r.activity_a)} {r.unit}</td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">{fmt(r.activity_b)} {r.unit}</td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">{fmt(r.activity_effect_t, 1)}</td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">{fmt(r.factor_effect_t, 1)}</td>
                      <td className="py-2.5 text-right font-medium tabular-nums">{fmt(r.change_t, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="muted mt-3 text-xs">Source: {res.source}. {res.note} Energy-use effect = change in use x earlier factor. Grid effect = later use x change in factor. They add up exactly to the total change.</p>
          </Card>
        </>
      )}
    </div>
  )
}
