/**
 * Simulation.jsx — What-if simulation page
 *
 * Computation runs entirely in the browser from dashboard.json (static site, no backend).
 * Formula: emission_kg = activity × factor (GHG Protocol accounting, NOT ML).
 * Factors come from the JSON (originally from src/emission_factors.py via dashboard_export.py).
 *
 * Only electricity (Scope 2) and generator diesel (Scope 1) are modelled.
 * Commuting and wastewater have no monthly time series; they are not simulated.
 */

import { useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Badge,
  Callout,
  Card,
  Kpi,
  Real,
  fmt,
  monthName,
  useChartTheme,
} from '../ui.jsx'
import { AlertTriangle, FlaskConical, Leaf, Zap } from 'lucide-react'

// ── JS accounting formula (mirrors src/simulation.py exactly) ─────────────────
function runScenario(baselineMonthly, electricityChangePct, dieselChangePct, solarOffsetKwhPerMonth, factors) {
  const ef = {}
  for (const f of factors) ef[f.name] = f
  const EF_ELEC = ef.electricity.factor   // kg CO2e / kWh
  const EF_DSEL = ef.diesel.factor        // kg CO2e / L

  let baseScope2 = 0, baseScope1 = 0
  let scenScope2 = 0, scenScope1 = 0

  const monthly = baselineMonthly.map((row) => {
    // baseline
    const baseElec = row.base_electricity_kwh
    const baseDiesel = row.base_diesel_litres
    const bScope2 = baseElec * EF_ELEC / 1000
    const bScope1 = baseDiesel * EF_DSEL / 1000
    baseScope2 += bScope2
    baseScope1 += bScope1

    // scenario
    const scenElec = Math.max(0, baseElec * (1 + electricityChangePct / 100) - solarOffsetKwhPerMonth)
    const scenDiesel = Math.max(0, baseDiesel * (1 + dieselChangePct / 100))
    const sScope2 = scenElec * EF_ELEC / 1000
    const sScope1 = scenDiesel * EF_DSEL / 1000
    scenScope2 += sScope2
    scenScope1 += sScope1

    return {
      month: row.month,
      label: monthName(row.month),
      base_total: +(bScope2 + bScope1).toFixed(4),
      scen_total: +(sScope2 + sScope1).toFixed(4),
      base_scope2: +bScope2.toFixed(4),
      base_scope1: +bScope1.toFixed(4),
      scen_scope2: +sScope2.toFixed(4),
      scen_scope1: +sScope1.toFixed(4),
    }
  })

  const baseTotal = +(baseScope2 + baseScope1).toFixed(4)
  const scenTotal = +(scenScope2 + scenScope1).toFixed(4)
  const savedTotal = +(baseTotal - scenTotal).toFixed(4)
  const savedPct = baseTotal > 0 ? +(savedTotal / baseTotal * 100).toFixed(2) : 0

  return {
    monthly,
    annual: {
      baseline_scope2_tco2e: +baseScope2.toFixed(4),
      baseline_scope1_tco2e: +baseScope1.toFixed(4),
      baseline_total_tco2e: baseTotal,
      scenario_scope2_tco2e: +scenScope2.toFixed(4),
      scenario_scope1_tco2e: +scenScope1.toFixed(4),
      scenario_total_tco2e: scenTotal,
      saved_tco2e: savedTotal,
      saved_pct: savedPct,
    },
  }
}

// ── compact axis tick formatter ────────────────────────────────────────────────
const compact = (v) => (Math.abs(v) >= 1 ? `${fmt(v, 1)}t` : `${fmt(v * 1000, 0)}kg`)

// ── slider input ───────────────────────────────────────────────────────────────
function SliderInput({ id, label, min, max, step = 1, value, onChange, unit = '%', accent = 'brand' }) {
  const pct = ((value - min) / (max - min)) * 100
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <label htmlFor={id} className="font-medium text-slate-700 dark:text-slate-300">{label}</label>
        <span className={`font-semibold ${value < 0 ? 'text-emerald-600 dark:text-emerald-400' : value > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-500'}`}>
          {value > 0 ? '+' : ''}{fmt(value, 0)}{unit}
        </span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-emerald-600"
        aria-label={label}
      />
      <div className="flex justify-between text-xs text-slate-400">
        <span>{min}{unit}</span>
        <span>0{unit}</span>
        <span>+{max}{unit}</span>
      </div>
    </div>
  )
}

// ── donut (simple CSS-based) ───────────────────────────────────────────────────
function ScopeDonut({ scope1, scope2, label }) {
  const total = scope1 + scope2 || 1
  const s2Pct = (scope2 / total * 100).toFixed(1)
  const s1Pct = (scope1 / total * 100).toFixed(1)
  const s2Deg = scope2 / total * 360
  return (
    <div className="flex flex-col items-center gap-3">
      <div
        className="relative h-28 w-28 rounded-full"
        style={{ background: `conic-gradient(#0f766e 0deg ${s2Deg}deg, #d97706 ${s2Deg}deg 360deg)` }}
        aria-label={`Scope 2: ${s2Pct}%, Scope 1: ${s1Pct}%`}
      >
        <div className="absolute inset-3 flex flex-col items-center justify-center rounded-full bg-white dark:bg-slate-900">
          <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 leading-tight">{fmt(scope1 + scope2, 1)}</span>
          <span className="text-[10px] text-slate-400">tCO₂e</span>
        </div>
      </div>
      <div className="text-center text-xs font-medium text-slate-600 dark:text-slate-400">{label}</div>
      <div className="flex gap-3 text-xs">
        <span className="flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-teal-700" />Scope 2 {s2Pct}%</span>
        <span className="flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-amber-600" />Scope 1 {s1Pct}%</span>
      </div>
    </div>
  )
}

// ── main page ──────────────────────────────────────────────────────────────────
export default function Simulation({ data }) {
  const sim = data.simulation
  const factors = sim.factors_used
  const cn = sim.coverage_note
  const t = useChartTheme()

  // controls
  const [elecPct, setElecPct] = useState(0)
  const [dselPct, setDselPct] = useState(0)
  const [solarKwh, setSolarKwh] = useState(0)

  const result = useMemo(
    () => runScenario(sim.baseline_monthly, elecPct, dselPct, solarKwh, factors),
    [sim.baseline_monthly, elecPct, dselPct, solarKwh, factors]
  )

  const ann = result.annual
  const isZero = elecPct === 0 && dselPct === 0 && solarKwh === 0
  const saved = ann.saved_tco2e
  const savedTone = saved > 0 ? 'green' : saved < 0 ? 'red' : 'slate'

  const elecFactor = factors.find((f) => f.name === 'electricity')
  const dselFactor = factors.find((f) => f.name === 'diesel')

  function applyPreset(p) {
    setElecPct(p.electricity_change_pct)
    setDselPct(p.diesel_change_pct)
    setSolarKwh(p.solar_offset_kwh_per_month)
  }

  function reset() {
    setElecPct(0)
    setDselPct(0)
    setSolarKwh(0)
  }

  return (
    <div className="space-y-6">
      {/* coverage callout */}
      <Callout title="Scope & coverage">
        This simulation models <strong>electricity (Scope 2)</strong> and <strong>generator diesel (Scope 1)</strong> only —
        covering ~<strong>{cn.covered_share_pct}%</strong> of the {fmt(cn.full_footprint_tco2e, 2)} tCO₂e campus footprint.{' '}
        <span className="italic">Commuting and wastewater have no monthly time series and are not simulated.</span>
      </Callout>

      {/* not covered */}
      <Callout tone="blue" title="Not covered by this simulation">
        <ul className="mt-1 list-disc pl-4 space-y-0.5">
          {cn.not_covered.map((nc, i) => <li key={i}>{nc}</li>)}
        </ul>
      </Callout>

      <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
        {/* ── controls panel ─────────────────────────────────────────────────── */}
        <div className="space-y-5">
          <Card title="Scenario controls" badge={<Badge tone="slate"><FlaskConical size={12} className="inline" /> Scenario</Badge>}>
            <div className="space-y-5">
              <SliderInput
                id="elec-slider"
                label="Grid electricity change"
                min={-100} max={50} step={1}
                value={elecPct}
                onChange={setElecPct}
              />
              <SliderInput
                id="diesel-slider"
                label="Generator diesel change"
                min={-100} max={50} step={1}
                value={dselPct}
                onChange={setDselPct}
              />
              <SliderInput
                id="solar-slider"
                label="Solar offset"
                min={0} max={30000} step={500}
                value={solarKwh}
                onChange={setSolarKwh}
                unit=" kWh/mo"
              />
              {data.solar && (
                <p className="muted -mt-3 text-xs leading-relaxed">
                  Existing rooftop solar (REAL): ~{fmt(data.solar.avg_kwh_per_month)} kWh/month, already self-consumed and not in the grid
                  figures above. This slider adds <em>new</em> solar on top.
                </p>
              )}
              <button
                onClick={reset}
                className="w-full rounded-xl border border-slate-200 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800 transition"
                id="sim-reset-btn"
              >
                Reset to baseline
              </button>
            </div>
          </Card>

          {/* presets */}
          <Card title="Illustrative presets" subtitle={sim.presets_note}>
            <div className="space-y-2">
              {sim.presets.map((p) => (
                <button
                  key={p.id}
                  id={`preset-${p.id}`}
                  onClick={() => applyPreset(p)}
                  className="w-full rounded-xl border border-dashed border-slate-200 p-3 text-left text-xs hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800 transition"
                >
                  <div className="font-semibold text-slate-800 dark:text-slate-200 mb-0.5">{p.label}</div>
                  <div className="text-slate-500 dark:text-slate-400 leading-relaxed">{p.description}</div>
                  <div className="mt-1.5 text-emerald-700 dark:text-emerald-400 font-medium">
                    Saves ≈ {fmt(p.annual.saved_tco2e, 1)} tCO₂e/yr ({fmt(p.annual.saved_pct, 1)}%)
                  </div>
                </button>
              ))}
            </div>
          </Card>

          {/* factor citation */}
          <Card title="Emission factors used" subtitle="Source from emission_factors.py">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-slate-400 border-b border-slate-100 dark:border-slate-800">
                  <th className="pb-1 text-left font-medium">Factor</th>
                  <th className="pb-1 text-right font-medium">Value</th>
                  <th className="pb-1 text-right font-medium">Scope</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                {[elecFactor, dselFactor].map((f) => f && (
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
            {[elecFactor, dselFactor].map((f) => f && (
              <p key={f.name} className="mt-1.5 text-[11px] text-slate-400 leading-relaxed">
                <strong className="capitalize">{f.name}</strong>: {f.source} · {f.version}
              </p>
            ))}
          </Card>
        </div>

        {/* ── results panel ──────────────────────────────────────────────────── */}
        <div className="space-y-5">
          {/* KPI row */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Kpi
              label="Baseline tCO₂e"
              value={fmt(ann.baseline_total_tco2e, 1)}
              unit="tCO₂e/yr"
              sub="REAL monthly × factor"
              badge={<Real />}
              icon={Zap}
            />
            <Kpi
              label="Scenario tCO₂e"
              value={fmt(ann.scenario_total_tco2e, 1)}
              unit="tCO₂e/yr"
              sub={isZero ? 'No changes applied' : 'After scenario'}
              badge={<Badge tone="slate"><FlaskConical size={11} className="inline" /> Scenario</Badge>}
              icon={FlaskConical}
            />
            <Kpi
              label={saved >= 0 ? 'Saved tCO₂e' : 'Added tCO₂e'}
              value={fmt(Math.abs(saved), 2)}
              unit="tCO₂e/yr"
              sub={`${saved >= 0 ? '−' : '+'}${fmt(Math.abs(ann.saved_pct), 1)}% vs baseline`}
              badge={<Badge tone={savedTone}>{saved >= 0 ? '↓ Reduction' : '↑ Increase'}</Badge>}
              icon={Leaf}
            />
            <Kpi
              label="Campus coverage"
              value={fmt(cn.covered_share_pct, 1)}
              unit="% of footprint"
              sub={`of ${fmt(cn.full_footprint_tco2e, 0)} tCO₂e total`}
              badge={<Badge tone="amber"><AlertTriangle size={11} className="inline" /> Partial</Badge>}
            />
          </div>

          {/* baseline vs scenario monthly chart */}
          <Card
            title="Monthly emissions: Baseline vs Scenario"
            subtitle="tCO₂e per month (REAL baseline, accounting formula)"
            badge={<Real />}
          >
            <div className="h-64">
              <ResponsiveContainer>
                <BarChart data={result.monthly} margin={{ left: -10 }} barGap={2}>
                  <CartesianGrid stroke={t.grid} vertical={false} />
                  <XAxis dataKey="label" stroke={t.axis} tickLine={false} />
                  <YAxis stroke={t.axis} tickLine={false} axisLine={false} tickFormatter={compact} width={52} unit="t" />
                  <Tooltip
                    contentStyle={t.tip}
                    formatter={(v, name) => [`${fmt(v, 3)} tCO₂e`, name]}
                    cursor={{ fill: 'rgba(148,163,184,0.1)' }}
                  />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                  <Bar isAnimationActive={false} dataKey="base_total" name="Baseline" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                  <Bar isAnimationActive={false} dataKey="scen_total" name="Scenario" fill="#0f766e" radius={[4, 4, 0, 0]} />
                  {!isZero && <ReferenceLine y={0} stroke={t.axis} />}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* scope breakdown chart */}
          <Card
            title="Scope 1 & 2 breakdown — Scenario"
            subtitle="tCO₂e per month (Scope 2 electricity + Scope 1 generator diesel)"
            badge={<Badge tone="slate"><FlaskConical size={11} className="inline" /> Scenario</Badge>}
          >
            <div className="h-64">
              <ResponsiveContainer>
                <BarChart data={result.monthly} margin={{ left: -10 }} stackOffset="sign">
                  <CartesianGrid stroke={t.grid} vertical={false} />
                  <XAxis dataKey="label" stroke={t.axis} tickLine={false} />
                  <YAxis stroke={t.axis} tickLine={false} axisLine={false} tickFormatter={compact} width={52} unit="t" />
                  <Tooltip
                    contentStyle={t.tip}
                    formatter={(v, name) => [`${fmt(v, 3)} tCO₂e`, name]}
                    cursor={{ fill: 'rgba(148,163,184,0.1)' }}
                  />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                  <Bar isAnimationActive={false} dataKey="scen_scope2" name="Scope 2 (electricity)" fill="#0f766e" stackId="a" radius={[0, 0, 0, 0]} />
                  <Bar isAnimationActive={false} dataKey="scen_scope1" name="Scope 1 (generator diesel)" fill="#d97706" stackId="a" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* annual donuts */}
          <Card title="Annual scope breakdown" subtitle="Baseline vs Scenario">
            <div className="flex flex-wrap justify-around gap-8 py-2">
              <ScopeDonut
                scope1={ann.baseline_scope1_tco2e}
                scope2={ann.baseline_scope2_tco2e}
                label="Baseline (REAL)"
              />
              <ScopeDonut
                scope1={ann.scenario_scope1_tco2e}
                scope2={ann.scenario_scope2_tco2e}
                label="Scenario"
              />
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
