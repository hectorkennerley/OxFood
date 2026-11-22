import { Bar, BarChart, CartesianGrid, Legend, Line, ComposedChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useApi } from '../api'

function heat(v: number | null) {
  if (v == null) return { background: '#f1f5f9', color: '#94a3b8' }
  const t = Math.max(0, Math.min(1, (v - 0.5) / 0.5))
  return { background: `rgba(0,33,71,${0.12 + t * 0.78})`, color: t > 0.45 ? 'white' : '#0f172a' }
}

export default function Forecast() {
  const { data: d } = useApi<any>('/forecast', 0)
  if (!d) return <div className="text-slate-500">Loading…</div>
  return (
    <div className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="h1">Bookings, attendance & covers forecast</h1>
        <p className="text-slate-500">Bookings come from the college system and attendance from card scans (pseudonymised). OxFood learns how many people really turn up.</p>
      </div>

      <div className="card overflow-hidden">
        <div className="p-4 font-bold">Next 7 days: how much to cook</div>
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-slate-500">
            <tr><th className="p-3">Service</th><th>Type</th><th className="text-right">Booked</th><th className="text-right">Show rate</th><th className="text-right">Expected</th><th className="text-right">Cook</th><th className="text-right">Saved vs booked+5%</th><th className="text-right pr-3">Staff</th></tr>
          </thead>
          <tbody>
            {d.upcoming.map((f: any) => (
              <tr key={f.service_id} className="border-t border-slate-100" title={f.explanation}>
                <td className="p-3 font-medium">{new Date(f.date).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })} · {f.meal}</td>
                <td><span className={`chip ${f.event_type === 'informal' ? 'bg-slate-100' : 'bg-ox text-white'}`}>{f.event_type.replace('_', ' ')}</span></td>
                <td className="text-right tabular-nums">{f.booked}</td>
                <td className="text-right tabular-nums">{Math.round(f.show_rate * 100)}%</td>
                <td className="text-right tabular-nums">{f.expected_covers}</td>
                <td className="text-right tabular-nums font-bold text-leaf-600">{f.recommended_portions}</td>
                <td className="text-right tabular-nums">{f.portions_saved} portions</td>
                <td className="text-right pr-3 tabular-nums">{f.staff_on_shift}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="card p-5">
          <div className="font-bold mb-3">Show-up rate by day and meal (last 6 weeks)</div>
          <table className="w-full text-sm text-center">
            <thead><tr className="text-slate-500"><th></th><th className="py-1">Breakfast</th><th>Lunch</th><th>Dinner</th></tr></thead>
            <tbody>
              {d.show_heatmap.map((r: any) => (
                <tr key={r.day}>
                  <td className="text-left font-semibold py-1 pr-2">{r.day}</td>
                  {['breakfast', 'lunch', 'dinner'].map((m) => (
                    <td key={m} className="p-1"><div className="rounded-lg py-2 font-semibold" style={heat(r[m])}>{r[m] == null ? '–' : `${Math.round(r[m] * 100)}%`}</div></td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex flex-wrap gap-2 mt-4">
            {d.by_event.map((e: any) => <span key={e.event_type} className="chip bg-ox-50 text-ox">{e.event_type.replace('_', ' ')}: {Math.round(e.show_rate * 100)}%</span>)}
          </div>
        </div>
        <div className="card p-5">
          <div className="font-bold">Who actually turns up</div>
          <p className="text-sm text-slate-500 mb-2">{d.students_tracked} students (pseudonymised IDs), last 28 days: share of booked meals each student attended. {d.no_show_meals_28d.toLocaleString()} booked meals were no-shows.</p>
          <ResponsiveContainer width="100%" height={230}>
            <BarChart data={d.habits}>
              <CartesianGrid stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="bucket" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="students" fill="#002147" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card p-5">
        <div className="font-bold mb-2">Last 2 weeks: booked vs attended vs cooked</div>
        <ResponsiveContainer width="100%" height={280}>
          <ComposedChart data={d.history}>
            <CartesianGrid stroke="#e2e8f0" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={2} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            <Bar dataKey="booked" fill="#cbd5e1" name="Booked" />
            <Bar dataKey="attended" fill="#002147" name="Attended (card scans)" />
            <Line dataKey="planned" stroke="#2f8f5b" strokeWidth={2} dot={false} name="Portions cooked" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
