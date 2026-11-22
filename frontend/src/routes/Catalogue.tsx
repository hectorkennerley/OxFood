import { Download, Minus, Plus, Search, Sparkles, Trash2 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { api, gbp, useApi } from '../api'

type Line = { product_id: number; name: string; supplier: string; qty: number; price: number; unit: string; pack_size: number; note?: string; fitWarn?: string }

export default function Catalogue() {
  const { data: products = [] } = useApi<any[]>('/catalogue', 0)
  const { data: orders = [], refetch: refetchOrders } = useApi<any[]>('/orders', 0)
  const [q, setQ] = useState('')
  const [cat, setCat] = useState('all')
  const [cart, setCart] = useState<Line[]>([])
  const [loading, setLoading] = useState(false)
  const [sugg, setSugg] = useState<any | null>(null)
  const [placed, setPlaced] = useState<any | null>(null)

  const cats = useMemo(() => ['all', ...Array.from(new Set(products.map((p) => p.category)))], [products])
  const shown = products.filter((p) => (cat === 'all' || p.category === cat) && (p.name + p.supplier).toLowerCase().includes(q.toLowerCase()))

  const add = (p: any, qty = 1) => setCart((c) => {
    const ex = c.find((l) => l.product_id === p.id)
    if (ex) return c.map((l) => (l.product_id === p.id ? { ...l, qty: l.qty + qty } : l))
    return [...c, { product_id: p.id, name: p.name, supplier: p.supplier, qty, price: p.price, unit: p.unit, pack_size: p.pack_size }]
  })
  const setQty = (id: number, qty: number) => setCart((c) => c.flatMap((l) => (l.product_id === id ? (qty > 0 ? [{ ...l, qty }] : []) : [l])))

  const loadSuggested = async () => {
    setLoading(true)
    const s = await api('/orders/suggested?days=3')
    setSugg(s)
    setCart(s.lines.filter((l: any) => l.supplier_active).map((l: any) => ({
      product_id: l.product_id, name: l.name, supplier: l.supplier, qty: l.qty, price: l.unit_price, unit: l.unit,
      pack_size: l.pack_size, note: `needs ${l.needed_units} ${l.unit}, ${l.in_stock_packs} in stock`,
      fitWarn: l.fit.fits ? undefined : l.fit.reason,
    })))
    setLoading(false)
  }

  const place = async () => {
    const o = await api('/orders', { body: { lines: cart.map((l) => ({ product_id: l.product_id, qty: l.qty })) } })
    setPlaced(o)
    setCart([])
    refetchOrders()
    window.location.href = `/api/orders/${o.id}/foodbuy.csv`
  }

  const total = cart.reduce((s, l) => s + l.qty * l.price, 0)
  const bySupplier = cart.reduce<Record<string, Line[]>>((acc, l) => ((acc[l.supplier] ||= []).push(l), acc), {})

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1fr_420px] gap-6 max-w-[1400px]">
      <div className="space-y-4">
        <div>
          <h1 className="h1">Order from your suppliers</h1>
          <p className="text-slate-500">Catalogue from your active distributors. Orders go to Foodbuy as a CSV.</p>
        </div>
        <div className="card p-5 bg-ox text-white flex items-center gap-4">
          <Sparkles />
          <div className="flex-1">
            <div className="font-bold">Suggested order for the next 3 days</div>
            <div className="text-sm text-white/80">Menu plan × forecast covers (not bookings) − stock already in date, rounded to packs, checked against fridge and freezer space.</div>
          </div>
          <button onClick={loadSuggested} disabled={loading} className="btn bg-white text-ox">{loading ? 'Working…' : 'Build suggested order'}</button>
        </div>
        {sugg && (
          <div className="text-sm text-slate-600">
            Covers {sugg.services} services ({sugg.start} → {sugg.end}). {sugg.lines.filter((l: any) => !l.supplier_active).length > 0 &&
              `${sugg.lines.filter((l: any) => !l.supplier_active).length} item(s) skipped: their supplier is inactive.`}
          </div>
        )}
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 text-slate-400" size={18} />
            <input className="input pl-10" placeholder="Search products or suppliers" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <select className="input w-44" value={cat} onChange={(e) => setCat(e.target.value)}>
            {cats.map((c) => <option key={c}>{c}</option>)}
          </select>
        </div>
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left">
              <tr className="text-slate-500"><th className="p-3">Product</th><th>Supplier</th><th>Pack</th><th>Storage</th><th className="text-right">Price</th><th></th></tr>
            </thead>
            <tbody>
              {shown.map((p) => (
                <tr key={p.id} className="border-t border-slate-100">
                  <td className="p-3 font-medium">{p.name}{p.allergens.length > 0 && <span className="text-xs text-slate-400 ml-2">{p.allergens.join(', ')}</span>}</td>
                  <td className="text-slate-600">{p.supplier}</td>
                  <td>{p.pack_size} {p.unit}</td>
                  <td><span className={`chip ${p.storage_type === 'frozen' ? 'bg-sky-100 text-sky-800' : p.storage_type === 'chilled' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{p.storage_type}</span></td>
                  <td className="text-right tabular-nums">{gbp(p.price)}</td>
                  <td className="text-right pr-3"><button className="btn-ghost !py-1 !px-2" onClick={() => add(p)}><Plus size={14} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <aside className="space-y-4">
        <div className="card p-5 sticky top-6">
          <div className="font-bold text-lg">Order basket</div>
          {cart.length === 0 && <p className="text-sm text-slate-500 mt-2">Empty. Build a suggested order or add products.</p>}
          <div className="mt-3 space-y-4 max-h-[55vh] overflow-auto pr-1">
            {Object.entries(bySupplier).map(([sup, lines]) => (
              <div key={sup}>
                <div className="label mb-1">{sup}</div>
                {lines.map((l) => (
                  <div key={l.product_id} className="py-1.5 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 text-sm font-medium">{l.name}</div>
                      <button onClick={() => setQty(l.product_id, l.qty - 1)} className="p-1 rounded bg-slate-100"><Minus size={12} /></button>
                      <span className="w-6 text-center text-sm tabular-nums">{l.qty}</span>
                      <button onClick={() => setQty(l.product_id, l.qty + 1)} className="p-1 rounded bg-slate-100"><Plus size={12} /></button>
                      <span className="w-16 text-right text-sm tabular-nums">{gbp(l.qty * l.price)}</span>
                      <button onClick={() => setQty(l.product_id, 0)} className="text-slate-400"><Trash2 size={14} /></button>
                    </div>
                    {l.note && <div className="text-[11px] text-slate-500">{l.note}</div>}
                    {l.fitWarn && <div className="text-[11px] text-red-600">⚠ {l.fitWarn}</div>}
                  </div>
                ))}
              </div>
            ))}
          </div>
          <div className="flex justify-between font-bold text-lg mt-4"><span>Total</span><span>{gbp(total)}</span></div>
          <button className="btn-green w-full mt-3 py-3" disabled={!cart.length} onClick={place}>
            <Download size={18} /> Place order · Foodbuy CSV
          </button>
          {placed && <div className="text-sm text-leaf-600 mt-2">Order OXF-{String(placed.id).padStart(5, '0')} placed ({gbp(placed.total)}). CSV downloaded.</div>}
        </div>
        <div className="card p-5">
          <div className="font-bold mb-2">Recent orders</div>
          <ul className="text-sm divide-y divide-slate-100">
            {orders.slice(0, 8).map((o) => (
              <li key={o.id} className="py-2 flex items-center gap-2">
                <span className="font-mono text-xs">OXF-{String(o.id).padStart(5, '0')}</span>
                <span className="text-slate-500 flex-1">{o.delivery_date} · {o.lines} lines</span>
                <span className="tabular-nums">{gbp(o.total)}</span>
                <a className="text-ox" href={`/api/orders/${o.id}/foodbuy.csv`} title="Download Foodbuy CSV"><Download size={14} /></a>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </div>
  )
}
