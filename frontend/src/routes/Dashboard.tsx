import { AlertTriangle, ArrowDownRight, ArrowUpRight, Users } from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  Bar, BarChart, CartesianGrid, Cell, Layer, Line, LineChart, Rectangle, ReferenceArea, ResponsiveContainer, Sankey,
  Tooltip, XAxis, YAxis,
} from 'recharts'
import { gbp, kg, useApi } from '../api'

const STAGE_COLOURS: Record<string, string> = {
  Overproduction: '#0b3b73', 'Servery leftover': '#2f8f5b', 'Plate waste': '#c27c0e', 'Prep trim': '#7c3aed',
  Spoilage: '#b91c1c', 'Cooking error': '#64748b',
}

function Kpi({ label, value, prev, better = 'down', fmt = (n: number) => String(n), sub }:
  { label: string; value: number; prev?: number; better?: 'up' | 'down'; fmt?: (n: number) => string; sub?: string }) {
  const delta = prev ? (value - prev) / prev : 0
  const good = better === 'down' ? delta < 0 : delta > 0
  return (
    <div className="card p-4">
      <div className="label">{label}</div>
      <div className="text-3xl font-bold text-ox mt-1 tabular-nums">{fmt(value)}</div>
      {prev != null && prev !== 0 && (
        <div className={`text-xs font-semibold mt-1 flex items-center gap-1 ${good ? 'text-leaf-600' : 'text-red-600'}`}>
          {delta < 0 ? <ArrowDownRight size={14} /> : <ArrowUpRight size={14} />}
          {Math.abs(delta * 100).toFixed(0)}% vs last week
        </div>
      )}
      {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
    </div>
  )
}

function SankeyNode({ x, y, width, height, index, payload }: any) {
  const colours = ['#002147', '#0b3b73', '#7c3aed', '#b91c1c', '#0b3b73', '#0b3b73', '#2f8f5b', '#2f8f5b', '#c27c0e', '#2f8f5b', '#94a3b8']
  const colour = colours[payload.key ?? index] ?? '#64748b'
  const right = x > 500
  return (
    <Layer key={`n${index}`}>
      <Rectangle x={x} y={y} width={width} height={height} fill={colour} fillOpacity={0.9} />
      <text x={right ? x - 6 : x + width + 6} y={y + height / 2} textAnchor={right ? 'end' : 'start'} dominantBaseline="middle"
        fontSize={12} fill="#1e293b" fontWeight={600}>
        {payload.name} <tspan fill="#64748b" fontWeight={400}>{Math.round(payload.value)} kg</tspan>
      </text>
    </Layer>
  )
}

export default function Dashboard() {
  const { data: d } = useApi<any>('/analytics/dashboard', 4000)
  if (!d) return <div className="text-slate-500">Loading…</div>
  const w = d.this_week
  const l = d.last_week
  const firstLive = d.trend.find((t: any) => t.live)?.week
  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="h1">Food waste dashboard</h1>
          <p className="text-slate-500">Last 7 days at St Edmund Hall. Updates live as the kitchen logs.</p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        <Kpi label="Food wasted" value={w.kg} prev={l.kg} fmt={(n) => kg(n)} />
        <Kpi label="Value wasted" value={w.gbp} prev={l.gbp} fmt={(n) => gbp(n, 0)} />
        <Kpi label="Waste per cover" value={w.g_per_cover} prev={l.g_per_cover} fmt={(n) => `${n} g`} sub={`${w.covers.toLocaleString()} covers`} />
        <Kpi label="Leftovers recovered" value={w.pct_recovered} prev={l.pct_recovered} better="up" fmt={(n) => `${n}%`} sub="of overproduction + servery" />
        <Kpi label="Value rescued" value={w.gbp_rescued} prev={l.gbp_rescued} better="up" fmt={(n) => gbp(n, 0)} sub="chilled, sold or reused" />
        <Kpi label="Surplus sales" value={w.gbp_sales} fmt={(n) => gbp(n)} sub={`${w.meals_claimed} meals claimed by students`} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="card p-5 xl:col-span-2 flex flex-col">
          <div className="flex items-center justify-between">
            <div className="font-bold">Waste per cover, 8 weeks</div>
            <div className="text-xs text-slate-500"><span className="inline-block w-3 h-3 bg-leaf-50 border border-leaf-100 mr-1 align-middle" />OxFood live</div>
          </div>
          <div className="flex-1 min-h-[240px]"><ResponsiveContainer width="100%" height="100%">
            <LineChart data={d.trend} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid stroke="#e2e8f0" vertical={false} />
              {firstLive && <ReferenceArea x1={firstLive} x2={d.trend[d.trend.length - 1].week} fill="#ebf7f0" />}
              <XAxis dataKey="week" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} unit=" g" />
              <Tooltip formatter={(v: any) => [`${v} g per cover`, '']} />
              <Line dataKey="g_per_cover" stroke="#002147" strokeWidth={3} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer></div>
        </div>

        <div className="card p-5">
          <div className="font-bold mb-3">Tonight</div>
          {d.tonight ? (
            <div>
              <div className="flex items-center gap-2 text-slate-500 text-sm"><Users size={16} /> {d.tonight.event_type.replace('_', ' ')} dinner · {d.tonight.staff_on_shift} staff</div>
              <div className="grid grid-cols-3 gap-2 my-3 text-center">
                <div><div className="text-2xl font-bold">{d.tonight.booked}</div><div className="label">booked</div></div>
                <div><div className="text-2xl font-bold">{Math.round(d.tonight.show_rate * 100)}%</div><div className="label">usually show</div></div>
                <div><div className="text-2xl font-bold text-leaf-600">{d.tonight.recommended_portions}</div><div className="label">cook</div></div>
              </div>
              <p className="text-sm text-slate-600">{d.tonight.explanation}</p>
              <p className="text-sm text-leaf-600 font-semibold mt-2">{d.tonight.portions_saved} fewer portions than cooking for everyone booked.</p>
            </div>
          ) : <div className="text-slate-500 text-sm">No dinner service today.</div>}
          <div className="font-bold mt-5 mb-2 flex items-center gap-2"><AlertTriangle size={16} className="text-amberx" /> Alerts</div>
          <ul className="space-y-1.5 text-sm max-h-48 overflow-auto">
            {d.alerts.slice(0, 8).map((a: any, i: number) => (
              <li key={i} className="flex gap-2">
                <span className={`mt-1.5 h-2 w-2 rounded-full shrink-0 ${a.level === 'red' ? 'bg-red-500' : 'bg-amber-500'}`} />
                {a.lot_id ? <Link className="hover:underline" to={`/journey/${a.lot_id}`}>{a.text}</Link> : <span>{a.text}</span>}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="card p-5">
        <div className="font-bold">Where last week's food went</div>
        <p className="text-sm text-slate-500">Every kilo from purchase to plate, by stage. Recovered = chilled for reuse, sold to students or used in stock.</p>
        <ResponsiveContainer width="100%" height={340}>
          <Sankey data={d.sankey} node={<SankeyNode />} nodePadding={24} nodeWidth={12}
            margin={{ top: 10, right: 160, bottom: 10, left: 10 }} link={{ stroke: '#94a3b8', strokeOpacity: 0.35 }}>
            <Tooltip formatter={(v: any) => `${v} kg`} />
          </Sankey>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card p-5">
          <div className="font-bold mb-2">By stage</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={d.by_stage} layout="vertical" margin={{ left: 30 }}>
              <XAxis type="number" tick={{ fontSize: 11 }} unit=" kg" />
              <YAxis type="category" dataKey="stage" tick={{ fontSize: 11 }} width={100} />
              <Tooltip formatter={(v: any) => `${v} kg`} />
              <Bar dataKey="kg" radius={[0, 6, 6, 0]}>
                {d.by_stage.map((s: any) => <Cell key={s.stage} fill={STAGE_COLOURS[s.stage] ?? '#64748b'} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card p-5">
          <div className="font-bold mb-2">Most over-produced dishes</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={d.top_dishes} layout="vertical" margin={{ left: 60 }}>
              <XAxis type="number" tick={{ fontSize: 11 }} unit=" kg" />
              <YAxis type="category" dataKey="dish" tick={{ fontSize: 10 }} width={140} />
              <Tooltip formatter={(v: any) => `${v} kg`} />
              <Bar dataKey="kg" fill="#0b3b73" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card p-5">
          <div className="font-bold mb-2">When food is wasted</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={d.by_hour}>
              <XAxis dataKey="hour" tick={{ fontSize: 10 }} interval={2} />
              <YAxis tick={{ fontSize: 11 }} unit=" kg" />
              <Tooltip formatter={(v: any) => `${v} kg`} />
              <Bar dataKey="kg" fill="#2f8f5b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
