import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Gauge, Ruler, Scale, Snowflake, Star } from 'lucide-react'
import { Badge, Callout, Card, Kpi, fmt, useChartTheme } from '../ui.jsx'

const TEAL = '#0f766e', SLATE = '#64748b', AMBER = '#d97706'

const signed = (n, d = 1) => `${n > 0 ? '+' : ''}${fmt(n, d)}`

function Verified({ ok }) {
  return ok ? <Badge tone="green">verified</Badge> : <Badge tone="amber">proxy, not verified</Badge>
}

function EpiChart({ a, refs }) {
  const t = useChartTheme()
  const rows = [
    { name: 'Campus (actual)', v: a.epi, fill: TEAL },
    ...refs.map((r) => ({ name: r.role === 'aspirational' ? 'Net-zero label' : '5-star cut-off', v: r.benchmark_epi, fill: r.role === 'aspirational' ? AMBER : SLATE })),
  ]
  return (
    <div className="h-64">
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ left: -5, top: 18 }}>
          <CartesianGrid stroke={t.grid} vertical={false} />
          <XAxis dataKey="name" stroke={t.axis} tickLine={false} />
          <YAxis stroke={t.axis} tickLine={false} axisLine={false} width={50} />
          <Tooltip cursor={false} contentStyle={t.tip} formatter={(v) => [`${fmt(v, 1)} ${a.epi_unit}`, 'EPI']} />
          <Bar dataKey="v" isAnimationActive={false} radius={[6, 6, 0, 0]}>
            {rows.map((r) => <Cell key={r.name} fill={r.fill} />)}
            <LabelList dataKey="v" position="top" formatter={(v) => fmt(v, 1)} fill={t.axis} fontSize={12} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function EnergyAudit({ data }) {
  const ea = data.energy_audit
  if (!ea) return <Callout tone="blue" title="Energy Audit data not available">This data file has no Energy Audit block. Run the pipeline again to create it.</Callout>
  const { actual: a, references: refs, ac } = ea
  const main = refs.find((r) => r.role === 'reference')
  const aspire = refs.find((r) => r.role === 'aspirational')
  const below = main.position === 'below_target'
  const cop = ac.assumed_cop
  const cp = ac.corrected_share_of_purchased
  const gh = ac.sanity_guest_house

  return (
    <div className="space-y-6">
      <Callout tone={below ? 'blue' : 'amber'} title={below ? 'The campus is already below the reference target' : 'The campus is above the reference target'}>
        Electricity use is {fmt(a.epi, 1)} {a.epi_unit}. The reference ({main.label}) is {fmt(main.benchmark_epi, 0)}, so the gap is{' '}
        <b>{signed(main.gap_tco2e)} tCO₂e</b> ({signed(main.gap_kwh, 0)} kWh). {below
          ? 'This page does not claim the campus is wasteful. A negative gap only means the reference is not the limit; what can still be reduced is a separate question and needs end-use data.'
          : 'The part above the reference is the first place to look for savings.'} The reference is a proxy, not an official educational-building benchmark.
      </Callout>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Electricity use index" value={fmt(a.epi, 1)} unit={a.epi_unit} sub={`${fmt(a.electricity_kwh)} kWh over ${fmt(a.built_up_area_m2)} m²`} icon={Gauge} />
        <Kpi label="Reference target" value={fmt(main.target_kwh)} unit="kWh / yr" sub={`${fmt(main.target_tco2e, 1)} tCO₂e at ${fmt(main.benchmark_epi, 0)} ${main.unit}`} icon={Ruler} badge={<Verified ok={main.verified} />} />
        <Kpi label="Gap to reference" value={signed(main.gap_tco2e)} unit="tCO₂e / yr" sub={below ? 'Negative: below the target' : 'Positive: above the target'} icon={Scale} />
        <Kpi label="Proxy star rating" value={`${a.proxy_star_rating} / 5`} sub="BEE office scheme, under 50% air-conditioned" icon={Star} badge={<Verified ok={false} />} />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Campus against the references" subtitle={`${a.epi_unit}, built-up area basis`} className="lg:col-span-2">
          <EpiChart a={a} refs={refs} />
        </Card>
        <Card title="Per person" subtitle="Context only, not a benchmark">
          <div className="text-3xl font-semibold tabular-nums">{fmt(a.kwh_per_person, 0)} <span className="muted text-sm font-normal">kWh / person / yr</span></div>
          <p className="muted mt-2 text-xs">{fmt(a.persons)} people on campus. Emission factor {a.grid_factor} {a.grid_factor_unit} ({a.grid_factor_source}).</p>
          <p className="muted mt-2 text-xs">Built-up area source: {a.area_source}.</p>
        </Card>
      </div>

      <Card title="References used" subtitle="Every value carries its source, version and unit">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="muted text-xs uppercase tracking-wide">
              <tr><th className="py-2 pr-4">Reference</th><th className="pr-4">EPI</th><th className="pr-4">Target tCO₂e</th><th className="pr-4">Gap tCO₂e</th><th className="pr-4">Source and version</th><th>Status</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {refs.map((r) => (
                <tr key={r.key} className="align-top">
                  <td className="py-2 pr-4 font-medium">{r.label}<div className="muted text-xs font-normal">{r.basis}</div></td>
                  <td className="pr-4 tabular-nums">{fmt(r.benchmark_epi, 0)} {r.unit}</td>
                  <td className="pr-4 tabular-nums">{fmt(r.target_tco2e, 1)}</td>
                  <td className="pr-4 tabular-nums">{signed(r.gap_tco2e)}</td>
                  <td className="pr-4 text-xs">{r.source}, {r.version}</td>
                  <td><Verified ok={r.verified} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted mt-3 text-xs">{ea.zone_note}</p>
        {aspire && <p className="muted mt-1 text-xs">The net-zero label is shown only to say how far the campus is from net-zero ({signed(aspire.gap_tco2e)} tCO₂e). It is not a target this audit asks for.</p>}
      </Card>

      <Card title="Air-conditioning check" subtitle={`${ac.units_total} units, ${ac.basis}`} badge={<Badge tone="amber">uses an ASSUMED COP</Badge>}>
        {ac.listed_kw_is_cooling_capacity && (
          <Callout tone="amber" title="The listed AC power looks like cooling capacity, not electrical input">
            The inventory lists about 3.5 kW per ton for every AC. One ton of refrigeration is {ac.ton_of_refrigeration_kw_thermal} kW of <i>cooling</i>, so the listed figure is the cooling capacity.
            Electrical input is about cooling capacity divided by COP. {ac.cop_label}
          </Callout>
        )}
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <Kpi label="As listed (modelled)" value={fmt(ac.modelled_kwh)} unit="kWh / yr" sub={`${fmt(ac.modelled_share_of_purchased * 100, 1)}% of purchased electricity`} icon={Snowflake} />
          <Kpi label={`Corrected, COP ${cop.central} (assumed)`} value={fmt(ac.corrected_kwh.central)} unit="kWh / yr" sub={`${fmt(cp.central * 100, 1)}% of purchased · ${fmt(ac.corrected_tco2e.central, 1)} tCO₂e`} icon={Snowflake} />
          <Kpi label={`Range, COP ${cop.low} to ${cop.high}`} value={`${fmt(ac.corrected_kwh.high / 1000)}k to ${fmt(ac.corrected_kwh.low / 1000)}k`} unit="kWh / yr" sub={`${fmt(cp.high * 100, 0)}% to ${fmt(cp.low * 100, 0)}% of purchased`} icon={Snowflake} />
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="muted text-xs uppercase tracking-wide">
              <tr><th className="py-2 pr-4">Location</th><th className="pr-4">Units</th><th className="pr-4">Listed kW / unit</th><th className="pr-4">Cooling kW / unit</th><th className="pr-4">Modelled kWh</th><th>Corrected kWh (COP {cop.high} to {cop.low})</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {ac.sites.map((s) => (
                <tr key={s.location}>
                  <td className="py-2 pr-4 font-medium">{s.location}</td>
                  <td className="pr-4 tabular-nums">{s.units}</td>
                  <td className="pr-4 tabular-nums">{fmt(s.listed_power_per_unit_kw, 2)}</td>
                  <td className="pr-4 tabular-nums">{fmt(s.cooling_capacity_per_unit_kw, 2)}</td>
                  <td className="pr-4 tabular-nums">{fmt(s.modelled_kwh)}</td>
                  <td className="tabular-nums">{fmt(s.corrected_kwh.high)} to {fmt(s.corrected_kwh.low)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {gh && (
          <p className="muted mt-3 text-xs">
            Sanity check, {gh.location} ({fmt(gh.area_m2)} m²): the listed figure means {fmt(gh.modelled_ac_kwh_per_m2, 0)} kWh/m² from air-conditioning alone; with the assumed COP it is {fmt(gh.corrected_ac_kwh_per_m2.high, 0)} to {fmt(gh.corrected_ac_kwh_per_m2.low, 0)} kWh/m². {gh.note}
          </p>
        )}
        <p className="muted mt-1 text-xs">{ac.note}</p>
      </Card>

      <Card title="Limits of this page">
        <ul className="list-disc space-y-1 pl-5 text-sm">
          {ea.caveats.map((c) => <li key={c}>{c}</li>)}
        </ul>
        <p className="muted mt-3 text-xs">Basis: {ea.basis}. Nothing on this page is predicted by machine learning.</p>
      </Card>
    </div>
  )
}

// Uploaded files have no building area or AC inventory, so the audit cannot be computed from them.
export function MyEnergyAudit() {
  return (
    <Callout tone="blue" title="Energy Audit needs building data">
      This page compares electricity use with a benchmark per square metre and checks an air-conditioner inventory, so it needs the built-up area and the AC list. An uploaded file does not carry them yet. Open the demo to see the page.
    </Callout>
  )
}
