import { Snowflake, Thermometer, Warehouse } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { gbp, useAction, useApi } from '../api'

const ICON: Record<string, any> = { fridge: Thermometer, freezer: Snowflake, dry: Warehouse }

export default function Inventory() {
  const { data } = useApi<any>('/inventory', 5000)
  const list = useAction<{ id: number; price: number }>((b) => `/inventory/${b.id}/list`)
  const [filter, setFilter] = useState<'all' | 'soon'>('soon')
  if (!data) return <div className="text-slate-500">Loading…</div>
  const lots = data.lots.filter((l: any) => filter === 'all' || l.days_to_expiry <= 3)

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="h1">Stock & storage</h1>
        <p className="text-slate-500">Every batch on site, its expiry, and the physical space it takes up.</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {data.storage.map((u: any) => {
          const Icon = ICON[u.type] ?? Warehouse
          return (
            <div key={u.id} className="card p-4">
              <div className="flex items-center gap-2 font-semibold"><Icon size={16} className="text-ox" /> {u.name}</div>
              <div className="h-3 rounded-full bg-slate-100 mt-3 overflow-hidden">
                <div className={`h-full ${u.pct > 85 ? 'bg-red-500' : u.pct > 65 ? 'bg-amber-500' : 'bg-leaf'}`} style={{ width: `${Math.min(100, u.pct)}%` }} />
              </div>
              <div className="text-xs text-slate-500 mt-1">{u.used_l} / {u.capacity_l} litres · {u.free_l} l free</div>
              {u.warnings.map((w: string) => <div key={w} className="text-xs text-amberx mt-1">⚠ {w}</div>)}
            </div>
          )
        })}
      </div>
      <div className="card overflow-hidden">
        <div className="p-4 flex items-center gap-2">
          <div className="font-bold flex-1">Batches</div>
          {(['soon', 'all'] as const).map((f) => (
            <button key={f} className={`chip !py-1.5 !px-3 ${filter === f ? 'bg-ox text-white' : 'bg-slate-100'}`} onClick={() => setFilter(f)}>
              {f === 'soon' ? 'Expiring within 3 days' : 'All stock'}
            </button>
          ))}
        </div>
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-slate-500">
            <tr><th className="p-3">Product</th><th>Qty</th><th>Where</th><th>Use by</th><th className="text-right">Value</th><th className="text-right pr-3">Action</th></tr>
          </thead>
          <tbody>
            {lots.map((l: any) => (
              <tr key={l.id} className="border-t border-slate-100">
                <td className="p-3 font-medium"><Link to={`/journey/${l.id}`} className="hover:underline">{l.product}</Link>
                  {l.source === 'transfer' && <span className="chip bg-leaf-50 text-leaf-600 ml-2">from marketplace</span>}</td>
                <td>{l.qty} × {l.pack_size}{l.unit}</td>
                <td className="text-slate-600">{l.storage_unit}</td>
                <td><span className={`chip ${l.days_to_expiry <= 0 ? 'bg-red-100 text-red-700' : l.days_to_expiry <= 2 ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'}`}>
                  {l.days_to_expiry <= 0 ? 'today' : `${l.days_to_expiry} days`}</span></td>
                <td className="text-right tabular-nums">{gbp(l.value_gbp)}</td>
                <td className="text-right pr-3">
                  {l.status === 'listed' ? <span className="chip bg-ox-50 text-ox">listed</span> : l.days_to_expiry >= 1 && (
                    <button className="btn-ghost !py-1 !px-2 text-xs" onClick={() => list.mutate({ id: l.id, price: Math.round(l.price * 0.5 * 2) / 2 })}>
                      List for colleges (50% off)
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
