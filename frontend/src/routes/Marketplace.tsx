import { CheckCircle2, XCircle } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { gbp, useAction, useApi } from '../api'

export default function Marketplace() {
  const { data = [] } = useApi<any[]>('/marketplace', 3000)
  const buy = useAction<{ id: number }>((b) => `/marketplace/${b.id}/buy`)
  const [bought, setBought] = useState<Record<number, any>>({})
  const [err, setErr] = useState<string | null>(null)
  const others = data.filter((l) => !l.mine)
  const mine = data.filter((l) => l.mine)

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="h1">College marketplace</h1>
        <p className="text-slate-500">Unopened, in-date stock other colleges can't use in time. Buy it before it becomes waste, if it fits your storage.</p>
      </div>
      {err && <div className="card p-3 bg-red-50 text-red-700 text-sm">{err}</div>}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {others.map((l) => {
          const done = bought[l.id]
          return (
            <div key={l.id} className="card p-5 flex flex-col">
              <div className="flex items-center gap-2">
                <span className="chip text-white" style={{ background: l.seller_colour }}>{l.seller}</span>
                <span className={`chip ${l.storage_type === 'frozen' ? 'bg-sky-100 text-sky-800' : l.storage_type === 'chilled' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100'}`}>{l.storage_type}</span>
                <span className="flex-1" />
                <span className={`chip ${l.days_to_expiry <= 2 ? 'bg-amber-100 text-amber-800' : 'bg-slate-100'}`}>use by {l.days_to_expiry}d</span>
              </div>
              <div className="font-bold text-lg mt-3">{l.product}</div>
              <div className="text-sm text-slate-500">{l.qty_remaining} × {l.pack_size}{l.unit} packs</div>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-2xl font-bold text-ox">{gbp(l.price)}</span>
                <span className="text-sm text-slate-400 line-through">{gbp(l.list_price)}</span>
                <span className="chip bg-leaf-50 text-leaf-600">{l.discount_pct}% off</span>
                <span className="text-xs text-slate-500">per pack</span>
              </div>
              {l.fit && (
                <div className={`mt-3 rounded-xl p-3 text-sm ${l.fit.fits ? 'bg-leaf-50 text-leaf-600' : 'bg-red-50 text-red-700'}`}>
                  <div className="flex items-center gap-2 font-semibold">{l.fit.fits ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                    {l.fit.fits ? `Fits your ${l.fit.unit_type}` : `Won't fit your ${l.fit.unit_type}`}</div>
                  <div className="text-xs mt-0.5">{l.fit.reason}</div>
                  {l.fit.warnings?.map((w: string) => <div key={w} className="text-xs mt-0.5">⚠ {w}</div>)}
                </div>
              )}
              <div className="flex-1" />
              {done ? (
                <Link to={`/journey/${done.lot.id}`} className="btn-ghost mt-4">✅ Bought for {gbp(done.claim.amount_gbp)}: see its journey</Link>
              ) : (
                <button className="btn-green mt-4" disabled={!l.fit?.fits || buy.isPending}
                  onClick={async () => {
                    setErr(null)
                    try { const r = await buy.mutateAsync({ id: l.id }); setBought((b) => ({ ...b, [l.id]: r })) } catch (e: any) { setErr(e.message) }
                  }}>
                  Buy all for {gbp(l.price * l.qty_remaining)}
                </button>
              )}
            </div>
          )
        })}
      </div>
      {mine.length > 0 && (
        <div className="card p-5">
          <div className="font-bold mb-2">Your listings</div>
          <ul className="text-sm space-y-1">{mine.map((l) => <li key={l.id}>{l.product}: {l.qty_remaining} left at {gbp(l.price)}</li>)}</ul>
        </div>
      )}
    </div>
  )
}
