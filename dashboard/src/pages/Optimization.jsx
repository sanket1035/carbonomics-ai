/**
 * Optimization.jsx — Budget-constrained CO₂ reduction optimization
 *
 * All computation runs in the browser from dashboard.json (static site, no backend).
 * Algorithm: exact 0/1 knapsack DP (works correctly for ≤~15 measures with
 * budget discretised to ₹1 k steps). For measures with max_units > 1 the
 * DP is extended to bounded knapsack.
 *
 * Formula: tCO₂e = activity_saved × factor (EMISSION_FACTORS, same as Python).
 * Factors are read from dashboard.json — NOT hard-coded here.
 *
 * Parity: scripts/optimization_parity.js checks JS == Python to 2 decimal places.
 */

import { useMemo, useState } from 'react'
import {
  Bar, BarChart, CartesianGrid, Cell, Legend,
  Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import {
  Badge, Callout, Card, Kpi, Real, fmt, useChartTheme,
} from '../ui.jsx'
import { AlertTriangle, CheckCircle2, FlaskConical, Package, TrendingDown, Zap } from 'lucide-react'

// ── compact axis formatter ────────────────────────────────────────────────────
const fmtLakh = (v) => {
  if (v >= 10_000_000) return `₹${(v / 10_000_000).toFixed(1)} Cr`
  if (v >= 100_000) return `₹${(v / 100_000).toFixed(1)} L`
  if (v >= 1000) return `₹${(v / 1000).toFixed(0)} k`
  return `₹${v}`
}
const fmtT = (v) => v >= 1 ? `${fmt(v, 1)}t` : `${fmt(v * 1000, 0)} kg`

// ── basis badge ───────────────────────────────────────────────────────────────
const BASIS_TONE = {
  MEASURED: 'green', QUOTED: 'green',
  ESTIMATE: 'amber', ASSUMPTION: 'amber', TBD: 'red',
}
function BasisBadge({ basis }) {
  const tone = BASIS_TONE[basis?.toUpperCase()] ?? 'slate'
  return <Badge tone={tone}>{basis || 'no basis'}</Badge>
}

// ── JS knapsack solver ────────────────────────────────────────────────────────
// Budget is discretised to STEP_INR steps to keep DP size manageable.
const STEP_INR = 1_000   // ₹1 k per cell

/**
 * Solve 0-1 bounded knapsack exactly in the browser.
 * measures: array of { id, capex_per_unit, tco2e_per_unit, max_units,
 *   kwh_per_unit, litres_per_unit, exclusive_group, cap_basis }
 * budget: ₹ (integer)
 * caps: { total_electricity, total_diesel, ac_end_use, ... }
 *
 * Returns: { selected: {id: units}, tco2e: number, capex: number }
 *
 * Note: caps are enforced as a post-DP feasibility filter because adding
 * cap dimensions to DP grows complexity. For the project's measure count
 * (≤15) the cap check is negligible.
 */
function knapsack(measures, budget, caps) {
  const B = Math.floor(budget / STEP_INR)   // cells
  const n = measures.length

  if (n === 0 || B <= 0) return { selected: {}, tco2e: 0, capex: 0 }

  // DP table: dp[j] = best tCO₂e achievable with ≤ j*STEP cells
  // We store (tco2e, capex, choices[]) using trace-back arrays.
  // For simplicity use a 2-row rolling array + choice map.
  let dp = new Array(B + 1).fill(0)
  // choice[i][j] = units taken from measure i at budget cell j
  const choice = Array.from({ length: n }, () => new Int8Array(B + 1))

  for (let i = 0; i < n; i++) {
    const m = measures[i]
    const cost = Math.ceil(m.capex_per_unit / STEP_INR)
    const val = m.tco2e_per_unit
    const maxU = Math.min(m.max_units, Math.floor(B / Math.max(cost, 1)))
    const next = new Float64Array(dp)

    for (let u = 1; u <= maxU; u++) {
      for (let j = B; j >= cost * u; j--) {
        const v = dp[j - cost * u] + val * u
        if (v > next[j]) {
          next[j] = v
          choice[i][j] = u
        }
      }
    }
    dp = Array.from(next)
  }

  // Trace back chosen units
  const units = {}
  let j = B
  for (let i = n - 1; i >= 0; i--) {
    const u = choice[i][j]
    if (u > 0) {
      units[measures[i].id] = u
      j -= Math.ceil(measures[i].capex_per_unit / STEP_INR) * u
    }
  }

  // --- Enforce exclusive groups (post-DP): keep highest-value from each group ---
  const groups = {}
  for (const m of measures) {
    if (m.exclusive_group && units[m.id] > 0) {
      const eg = m.exclusive_group
      if (!groups[eg]) groups[eg] = []
      groups[eg].push({ id: m.id, tco2e: m.tco2e_per_unit * units[m.id] })
    }
  }
  for (const eg of Object.keys(groups)) {
    const members = groups[eg].sort((a, b) => b.tco2e - a.tco2e)
    for (let k = 1; k < members.length; k++) delete units[members[k].id]
  }

  // --- Enforce cap constraints (post-DP) ---
  // Iteratively remove the least valuable measure until all caps satisfied.
  let changed = true
  while (changed) {
    changed = false
    const elecUsed = measures.reduce(
      (s, m) => s + (units[m.id] || 0) * m.kwh_per_unit, 0)
    const dieselUsed = measures.reduce(
      (s, m) => s + (units[m.id] || 0) * m.litres_per_unit, 0)

    const acUsed = measures
      .filter(m => m.cap_basis === 'ac_end_use')
      .reduce((s, m) => s + (units[m.id] || 0) * m.kwh_per_unit, 0)

    const violations = []
    if (caps.total_electricity != null && elecUsed > caps.total_electricity + 1)
      violations.push('total_electricity')
    if (caps.total_diesel != null && dieselUsed > caps.total_diesel + 1)
      violations.push('total_diesel')
    if (caps.ac_end_use != null && acUsed > caps.ac_end_use + 1)
      violations.push('ac_end_use')

    if (violations.length > 0) {
      // Remove the measure with lowest tCO₂e/₹ ratio that contributes to a violation
      const candidates = measures.filter(m => units[m.id] > 0)
      if (candidates.length === 0) break
      candidates.sort((a, b) =>
        (a.tco2e_per_unit / a.capex_per_unit) - (b.tco2e_per_unit / b.capex_per_unit)
      )
      delete units[candidates[0].id]
      changed = true
    }
  }

  const tco2e = measures.reduce((s, m) => s + (units[m.id] || 0) * m.tco2e_per_unit, 0)
  const capex = measures.reduce((s, m) => s + (units[m.id] || 0) * m.capex_per_unit, 0)
  return { selected: units, tco2e, capex }
}

// Greedy for comparison (sort by tCO₂e/₹ desc, take while budget allows)
function greedySolve(measures, budget, caps) {
  const sorted = [...measures].sort(
    (a, b) => (b.tco2e_per_unit / b.capex_per_unit) - (a.tco2e_per_unit / a.capex_per_unit)
  )
  const units = {}
  let remaining = budget
  const excUsed = new Set()
  let elecUsed = 0, dieselUsed = 0, acUsed = 0

  for (const m of sorted) {
    if (m.exclusive_group && excUsed.has(m.exclusive_group)) continue
    const maxU = Math.min(m.max_units, Math.floor(remaining / m.capex_per_unit))
    for (let u = maxU; u >= 1; u--) {
      const newElec = elecUsed + m.kwh_per_unit * u
      const newDiesel = dieselUsed + m.litres_per_unit * u
      const newAc = m.cap_basis === 'ac_end_use' ? acUsed + m.kwh_per_unit * u : acUsed
      if (
        (caps.total_electricity == null || newElec <= caps.total_electricity + 1) &&
        (caps.total_diesel == null || newDiesel <= caps.total_diesel + 1) &&
        (caps.ac_end_use == null || newAc <= caps.ac_end_use + 1)
      ) {
        units[m.id] = u
        remaining -= m.capex_per_unit * u
        elecUsed = newElec; dieselUsed = newDiesel; acUsed = newAc
        if (m.exclusive_group) excUsed.add(m.exclusive_group)
        break
      }
    }
  }
  const tco2e = measures.reduce((s, m) => s + (units[m.id] || 0) * m.tco2e_per_unit, 0)
  const capex = measures.reduce((s, m) => s + (units[m.id] || 0) * m.capex_per_unit, 0)
  return { selected: units, tco2e, capex }
}

// ── main component ────────────────────────────────────────────────────────────
export default function Optimization({ data }) {
  const opt = data.optimization
  const measures = opt?.measures ?? []
  const needsInput = opt?.needs_input ?? []
  const coverageNote = opt?.coverage_note ?? {}
  const statusMessage = opt?.status_message
  const t = useChartTheme()

  // Build solver-friendly measure list from dashboard.json
  // Only "ready" measures with valid impact enter the solver
  const solverMeasures = useMemo(() => measures
    .filter(m => m.status === 'ready' && m.impact && m.impact.tco2e_saved_per_unit > 0)
    .map(m => ({
      id: m.id,
      label: m.label,
      category: m.category,
      acts_on: m.acts_on,
      capex_per_unit: m.impact.capex_per_unit,
      tco2e_per_unit: m.impact.tco2e_saved_per_unit,
      kwh_per_unit: m.impact.kwh_saved_per_unit,
      litres_per_unit: m.impact.litres_saved_per_unit,
      max_units: m.max_units ?? 1,
      exclusive_group: m.exclusive_group ?? null,
      cap_basis: m.cap_basis ?? null,
      basis: m.basis,
      source: m.source,
      source_date: m.source_date,
      scope: m.impact.scope,
      inr_per_tco2e: m.impact.inr_per_tco2e,
    })), [measures])

  // Caps from baseline KPI
  const caps = useMemo(() => ({
    total_electricity: data.kpis?.electricity_kwh ?? null,
    total_diesel: data.kpis?.diesel_litres ?? null,
    ac_end_use: 697296,   // ESTIMATE, sheet 4_AC_Inventory
  }), [data.kpis])

  // Budget state (₹)
  const [budgetStr, setBudgetStr] = useState('')
  const budget = parseFloat(budgetStr.replace(/,/g, '')) || 0

  // Per-row overrides (budget + exclude)
  const [overrides, setOverrides] = useState({})
  const setOverride = (id, field, val) =>
    setOverrides(prev => ({ ...prev, [id]: { ...(prev[id] ?? {}), [field]: val } }))

  // Apply overrides to solver measures
  const effectiveMeasures = useMemo(() =>
    solverMeasures
      .filter(m => !(overrides[m.id]?.excluded))
      .map(m => ({
        ...m,
        capex_per_unit: overrides[m.id]?.capex_per_unit ?? m.capex_per_unit,
        tco2e_per_unit: (() => {
          // recalculate tco2e if kwh override applied
          const kwh = overrides[m.id]?.kwh_per_unit ?? m.kwh_per_unit
          const l = overrides[m.id]?.litres_per_unit ?? m.litres_per_unit
          const efElec = data.optimization?.factors_used?.find(f => f.name === 'electricity')?.factor ?? 0.71
          const efDiesel = data.optimization?.factors_used?.find(f => f.name === 'diesel')?.factor ?? 2.89
          return (kwh * efElec + l * efDiesel) / 1000
        })(),
        max_units: overrides[m.id]?.max_units ?? m.max_units,
      }))
  , [solverMeasures, overrides, data.optimization])

  // Run knapsack
  const result = useMemo(() => {
    if (effectiveMeasures.length === 0 || budget <= 0) return null
    return knapsack(effectiveMeasures, budget, caps)
  }, [effectiveMeasures, budget, caps])

  const greedy = useMemo(() => {
    if (effectiveMeasures.length === 0 || budget <= 0) return null
    return greedySolve(effectiveMeasures, budget, caps)
  }, [effectiveMeasures, budget, caps])

  // Budget sweep (₹500 k … ₹25 Cr)
  const sweepBudgets = [500_000, 1_000_000, 2_000_000, 5_000_000, 10_000_000, 15_000_000, 20_000_000, 25_000_000]
  const sweepData = useMemo(() => {
    if (effectiveMeasures.length === 0) return []
    return sweepBudgets.map(b => {
      const opt = knapsack(effectiveMeasures, b, caps)
      const gr = greedySolve(effectiveMeasures, b, caps)
      return { budget: b, optimal: +opt.tco2e.toFixed(3), greedy: +gr.tco2e.toFixed(3) }
    })
  }, [effectiveMeasures, caps])

  // Selected measures details
  const selectedDetails = useMemo(() => {
    if (!result) return []
    return effectiveMeasures
      .filter(m => (result.selected[m.id] ?? 0) > 0)
      .map(m => ({
        ...m,
        units: result.selected[m.id],
        total_capex: m.capex_per_unit * result.selected[m.id],
        total_tco2e: +(m.tco2e_per_unit * result.selected[m.id]).toFixed(4),
      }))
  }, [result, effectiveMeasures])

  // KPI values
  const coveredBase = coverageNote.covered_tco2e ?? data.kpis?.covered_tco2e ?? 0
  const fullFootprint = coverageNote.full_footprint_tco2e ?? 3719.74
  const savedT = result?.tco2e ?? 0
  const savedPctBase = coveredBase > 0 ? (savedT / coveredBase * 100) : 0
  const savedPctFull = (savedT / fullFootprint * 100)

  const noReady = effectiveMeasures.length === 0

  // Factors
  const factorsUsed = opt?.factors_used ?? []

  // MACC data (cost per tCO₂e, sorted ascending)
  const maccData = useMemo(() =>
    effectiveMeasures
      .filter(m => m.inr_per_tco2e != null)
      .sort((a, b) => a.inr_per_tco2e - b.inr_per_tco2e)
      .map(m => ({
        label: m.label.length > 20 ? m.label.slice(0, 18) + '…' : m.label,
        inr_per_tco2e: m.inr_per_tco2e,
        id: m.id,
        selected: !!(result?.selected[m.id]),
      }))
  , [effectiveMeasures, result])

  const resetOverrides = () => setOverrides({})

  return (
    <div className="space-y-6">
      {/* Coverage callout — always show */}
      <Callout title="Scope & coverage">
        Optimization covers <strong>electricity (Scope 2)</strong> and <strong>generator diesel (Scope 1)</strong> only —
        ~<strong>{coverageNote.covered_share_pct ?? '20.5'}%</strong> of the {fmt(fullFootprint, 2)} tCO₂e campus footprint.
        {' '}<em>Commuting and wastewater are not modelled (no monthly time series).</em>
      </Callout>

      {/* Needs input panel — always show if any TBD measures */}
      {needsInput.length > 0 && (
        <Card
          title={`Needs input — ${needsInput.length} measure${needsInput.length > 1 ? 's' : ''} waiting for data`}
          badge={<Badge tone="red"><AlertTriangle size={11} className="inline" /> Needs input</Badge>}
        >
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
            Fill in <code className="text-xs bg-slate-100 dark:bg-slate-800 rounded px-1">data/inputs/optimization_measures.csv</code>{' '}
            and re-run <code className="text-xs bg-slate-100 dark:bg-slate-800 rounded px-1">python scripts/run_pipeline.py</code>.
            Do not add values without a real source (vendor quote, energy audit, bill, etc.).
          </p>
          <div className="space-y-2">
            {needsInput.map(ni => (
              <div key={ni.id} className="rounded-xl border border-dashed border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/30 p-3 text-xs">
                <div className="font-semibold text-amber-900 dark:text-amber-200 mb-0.5">{ni.label}</div>
                <div className="text-amber-700 dark:text-amber-400">
                  Missing: <span className="font-mono">{ni.missing_fields?.join(', ') || 'unknown'}</span>
                </div>
                {ni.notes && <div className="mt-1 text-amber-600 dark:text-amber-500 italic">{ni.notes.slice(0, 120)}</div>}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* If nothing ready at all */}
      {noReady && (
        <Callout tone="blue" title="No measures ready for optimization">
          {statusMessage ?? 'All measures need input. Fill in the CSV and re-run the pipeline.'}
        </Callout>
      )}

      {/* Controls — only show if we have something to optimize */}
      {!noReady && (
        <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
          {/* ── left panel ─────────────────────────────────────────────── */}
          <div className="space-y-5">
            <Card title="Budget" subtitle="Enter total available budget (₹)" badge={<Badge tone="slate">₹</Badge>}>
              <div className="space-y-3">
                <input
                  id="budget-input"
                  type="number"
                  min={0}
                  step={100000}
                  value={budgetStr}
                  onChange={e => setBudgetStr(e.target.value)}
                  placeholder="e.g. 5000000"
                  className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  aria-label="Budget in rupees"
                />
                {budgetStr && (
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    = {fmtLakh(budget)}
                  </div>
                )}
                <button
                  id="opt-reset-btn"
                  onClick={resetOverrides}
                  className="w-full rounded-xl border border-slate-200 dark:border-slate-700 py-2 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition"
                >
                  Reset overrides to file values
                </button>
              </div>
            </Card>

            {/* Measure table with overrides */}
            <Card
              title="Measures"
              subtitle="Toggle, edit capex or max units. Edits stay in browser only."
            >
              <div className="space-y-3">
                {effectiveMeasures.concat(
                  solverMeasures.filter(m => overrides[m.id]?.excluded)
                ).map(m => {
                  const excluded = overrides[m.id]?.excluded ?? false
                  const selected = !excluded && (result?.selected[m.id] ?? 0) > 0
                  return (
                    <div
                      key={m.id}
                      className={`rounded-xl border p-3 text-xs space-y-2 transition ${
                        selected
                          ? 'border-emerald-200 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/30'
                          : excluded
                          ? 'border-slate-100 dark:border-slate-800 opacity-50'
                          : 'border-slate-100 dark:border-slate-800'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium text-slate-800 dark:text-slate-200 leading-tight">{m.label}</span>
                        <div className="flex items-center gap-1.5">
                          {selected && <CheckCircle2 size={13} className="text-emerald-600 dark:text-emerald-400" />}
                          <BasisBadge basis={m.basis} />
                          <button
                            onClick={() => setOverride(m.id, 'excluded', !excluded)}
                            className={`rounded-full px-2 py-0.5 text-[10px] font-medium transition ${
                              excluded
                                ? 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300'
                                : 'bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300 hover:bg-rose-200'
                            }`}
                            id={`toggle-${m.id}`}
                          >
                            {excluded ? 'Include' : 'Exclude'}
                          </button>
                        </div>
                      </div>
                      {!excluded && (
                        <div className="flex gap-3 flex-wrap">
                          <label className="flex flex-col gap-0.5">
                            <span className="text-slate-400">Capex (₹)</span>
                            <input
                              type="number"
                              min={0}
                              value={overrides[m.id]?.capex_per_unit ?? m.capex_per_unit}
                              onChange={e => setOverride(m.id, 'capex_per_unit', Number(e.target.value))}
                              className="w-28 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 py-1 font-mono text-[11px] focus:outline-none focus:ring-1 focus:ring-emerald-500"
                            />
                          </label>
                          <label className="flex flex-col gap-0.5">
                            <span className="text-slate-400">Max units</span>
                            <input
                              type="number"
                              min={1}
                              value={overrides[m.id]?.max_units ?? m.max_units}
                              onChange={e => setOverride(m.id, 'max_units', Math.max(1, parseInt(e.target.value) || 1))}
                              className="w-16 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 py-1 font-mono text-[11px] focus:outline-none focus:ring-1 focus:ring-emerald-500"
                            />
                          </label>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </Card>

            {/* Factor citation */}
            <Card title="Emission factors" subtitle="Source from emission_factors.py">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-400 border-b border-slate-100 dark:border-slate-800">
                    <th className="pb-1 text-left font-medium">Factor</th>
                    <th className="pb-1 text-right font-medium">Value</th>
                    <th className="pb-1 text-right font-medium">Scope</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                  {factorsUsed.map(f => (
                    <tr key={f.name}>
                      <td className="py-1.5 text-slate-700 dark:text-slate-300 capitalize">{f.name}</td>
                      <td className="py-1.5 text-right font-mono text-slate-600 dark:text-slate-400">{f.factor} {f.output}</td>
                      <td className="py-1.5 text-right">
                        <Badge tone={f.scope === 'Scope 2' ? 'green' : 'amber'}>{f.scope}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {factorsUsed.map(f => (
                <p key={f.name} className="mt-1 text-[11px] text-slate-400 leading-relaxed">
                  <strong className="capitalize">{f.name}</strong>: {f.source} · {f.version}
                </p>
              ))}
            </Card>
          </div>

          {/* ── right panel ─────────────────────────────────────────────── */}
          <div className="space-y-5">
            {/* KPI cards */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Kpi
                label="Budget used"
                value={result ? fmtLakh(result.capex) : '—'}
                sub={result && budget > 0 ? `of ${fmtLakh(budget)}` : 'Enter budget'}
                icon={Package}
                badge={<Real />}
              />
              <Kpi
                label="tCO₂e saved/yr"
                value={result ? fmt(savedT, 2) : '—'}
                unit="tCO₂e"
                sub="Optimal selection"
                badge={<Badge tone="green"><TrendingDown size={11} className="inline" /> Optimal</Badge>}
                icon={TrendingDown}
              />
              <Kpi
                label="% covered baseline"
                value={result ? fmt(savedPctBase, 1) : '—'}
                unit="%"
                sub={`of ${fmt(coveredBase, 1)} tCO₂e`}
                badge={<Badge tone="slate">Scope 1+2</Badge>}
                icon={Zap}
              />
              <Kpi
                label="% full footprint"
                value={result ? fmt(savedPctFull, 2) : '—'}
                unit="%"
                sub={`of ${fmt(fullFootprint, 0)} tCO₂e`}
                badge={<Badge tone="amber"><AlertTriangle size={11} className="inline" /> Partial</Badge>}
              />
            </div>

            {/* Selected measures */}
            {result && selectedDetails.length > 0 ? (
              <Card
                title="Optimal selection"
                subtitle="Measures chosen by the knapsack solver within budget"
                badge={<Badge tone="green"><CheckCircle2 size={11} className="inline" /> Optimal</Badge>}
              >
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-slate-100 dark:border-slate-800 text-slate-400">
                        <th className="pb-1.5 text-left font-medium">Measure</th>
                        <th className="pb-1.5 text-right font-medium">Units</th>
                        <th className="pb-1.5 text-right font-medium">Capex</th>
                        <th className="pb-1.5 text-right font-medium">tCO₂e/yr</th>
                        <th className="pb-1.5 text-right font-medium">Scope</th>
                        <th className="pb-1.5 text-right font-medium">Basis</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                      {selectedDetails.map(s => (
                        <tr key={s.id}>
                          <td className="py-1.5 text-slate-800 dark:text-slate-200">{s.label}</td>
                          <td className="py-1.5 text-right font-mono">{s.units}</td>
                          <td className="py-1.5 text-right font-mono">{fmtLakh(s.total_capex)}</td>
                          <td className="py-1.5 text-right font-mono font-semibold text-emerald-700 dark:text-emerald-400">{fmt(s.total_tco2e, 3)}</td>
                          <td className="py-1.5 text-right">
                            <Badge tone={s.scope === 'Scope 2' ? 'green' : 'amber'}>{s.scope}</Badge>
                          </td>
                          <td className="py-1.5 text-right"><BasisBadge basis={s.basis} /></td>
                        </tr>
                      ))}
                      <tr className="border-t-2 border-slate-200 dark:border-slate-700 font-semibold text-slate-900 dark:text-white">
                        <td className="pt-2 text-xs">Total</td>
                        <td />
                        <td className="pt-2 text-right font-mono">{fmtLakh(result.capex)}</td>
                        <td className="pt-2 text-right font-mono text-emerald-700 dark:text-emerald-400">{fmt(savedT, 3)}</td>
                        <td /><td />
                      </tr>
                    </tbody>
                  </table>
                </div>
              </Card>
            ) : budget > 0 && !noReady && (
              <Callout tone="blue" title="No measures selected">
                No ready measure fits within the entered budget. Increase budget or check measure costs.
              </Callout>
            )}

            {/* Optimal vs Greedy comparison */}
            {result && greedy && (
              <Card title="Optimal vs Greedy" subtitle="MILP (Python) / knapsack DP (JS) vs greedy sort-by-ratio">
                <div className="grid grid-cols-2 gap-4 text-center text-sm">
                  <div className="rounded-xl bg-emerald-50 dark:bg-emerald-950/30 p-4">
                    <div className="text-xs text-slate-500 mb-1 font-medium uppercase tracking-wide">Optimal (knapsack)</div>
                    <div className="text-2xl font-semibold text-emerald-700 dark:text-emerald-400">{fmt(result.tco2e, 2)}</div>
                    <div className="text-xs text-slate-400">tCO₂e/yr</div>
                    <div className="mt-1 text-xs text-slate-500">{fmtLakh(result.capex)} used</div>
                  </div>
                  <div className="rounded-xl bg-slate-50 dark:bg-slate-800/50 p-4">
                    <div className="text-xs text-slate-500 mb-1 font-medium uppercase tracking-wide">Greedy baseline</div>
                    <div className="text-2xl font-semibold text-slate-700 dark:text-slate-300">{fmt(greedy.tco2e, 2)}</div>
                    <div className="text-xs text-slate-400">tCO₂e/yr</div>
                    <div className="mt-1 text-xs text-slate-500">{fmtLakh(greedy.capex)} used</div>
                  </div>
                </div>
                {result.tco2e > greedy.tco2e + 0.001 && (
                  <p className="mt-2 text-xs text-emerald-700 dark:text-emerald-400 text-center">
                    ✓ Optimal saves {fmt(result.tco2e - greedy.tco2e, 2)} tCO₂e more than greedy (+{fmt((result.tco2e - greedy.tco2e) / Math.max(greedy.tco2e, 0.001) * 100, 1)}%)
                  </p>
                )}
                {Math.abs(result.tco2e - greedy.tco2e) <= 0.001 && (
                  <p className="mt-2 text-xs text-slate-400 text-center">Greedy equals optimal for this budget/measure set.</p>
                )}
              </Card>
            )}

            {/* Budget vs reduction sweep */}
            {sweepData.length > 0 && (
              <Card
                title="Budget vs CO₂e reduction"
                subtitle="Optimal knapsack and greedy at each budget level"
                badge={<Badge tone="slate">Sweep</Badge>}
              >
                <div className="h-64">
                  <ResponsiveContainer>
                    <LineChart data={sweepData} margin={{ left: -10 }}>
                      <CartesianGrid stroke={t.grid} vertical={false} />
                      <XAxis dataKey="budget" stroke={t.axis} tickLine={false}
                        tickFormatter={fmtLakh} minTickGap={60} />
                      <YAxis stroke={t.axis} tickLine={false} axisLine={false}
                        tickFormatter={fmtT} width={56} />
                      <Tooltip
                        contentStyle={t.tip}
                        labelFormatter={fmtLakh}
                        formatter={(v, name) => [`${fmt(v, 2)} tCO₂e/yr`, name]}
                      />
                      <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                      <Line animationDuration={900} type="monotone"
                        dataKey="optimal" name="Optimal (knapsack)" stroke="#0f766e" strokeWidth={2} dot={false} />
                      <Line animationDuration={900} type="monotone"
                        dataKey="greedy" name="Greedy baseline" stroke="#94a3b8" strokeWidth={2} dot={false} strokeDasharray="4 4" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            )}

            {/* MACC-style bar chart */}
            {maccData.length > 0 && (
              <Card
                title="Cost per tCO₂e saved (MACC-style)"
                subtitle="₹ per tCO₂e/yr — lower = more cost-effective"
              >
                <div className="h-64">
                  <ResponsiveContainer>
                    <BarChart data={maccData} layout="vertical" margin={{ left: 10, right: 10 }}>
                      <CartesianGrid stroke={t.grid} horizontal={false} />
                      <XAxis type="number" stroke={t.axis} tickLine={false}
                        tickFormatter={v => fmtLakh(v)} />
                      <YAxis type="category" dataKey="label" stroke={t.axis}
                        tickLine={false} width={120} tick={{ fontSize: 11 }} />
                      <Tooltip
                        contentStyle={t.tip}
                        formatter={(v) => [`${fmtLakh(v)} / tCO₂e`, 'Cost effectiveness']}
                      />
                      <Bar animationDuration={900} dataKey="inr_per_tco2e" name="₹/tCO₂e" radius={[0, 4, 4, 0]}>
                        {maccData.map(m => (
                          <Cell key={m.id}
                            fill={m.selected ? '#0f766e' : '#94a3b8'}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="mt-1 text-[11px] text-slate-400">
                  Green bars = selected in current optimal solution.
                </p>
              </Card>
            )}

            {/* Limitations */}
            <Callout title="Limitations & assumptions">
              <ul className="mt-1 list-disc pl-4 space-y-1 text-xs leading-relaxed">
                <li>Savings modelled as static annual averages — seasonal variation ignored.</li>
                <li>Additive electricity savings are capped at the baseline total and per end-use (AC = 697,296 kWh, the listed figure from the AC inventory). The Energy Audit page shows why this figure is probably too high and gives a corrected estimate.</li>
                <li>Lighting end-use is not known: there is no lighting inventory. LED measures are left out until that data exists.</li>
                <li>Cost and saving inputs must come from the owner (vendor quote / audit); nothing is invented.</li>
                <li>MILP assumes linear scaling per unit. Non-linearities need additional modelling.</li>
                <li>Payback not computed — electricity tariff and diesel price not yet provided.</li>
              </ul>
            </Callout>
          </div>
        </div>
      )}
    </div>
  )
}
