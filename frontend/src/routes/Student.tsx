import { Bell, Clock, MapPin } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api, gbp, useApi } from '../api'

function minsLeft(iso: string) {
  return Math.max(0, Math.round((new Date(iso).getTime() - Date.now()) / 60000))
}

export default function Student() {
  const { data, refetch } = useApi<any>('/student/feed', 2500)
  const [toast, setToast] = useState<any | null>(null)
  const [codes, setCodes] = useState<Record<number, string>>({})
  const [err, setErr] = useState<string | null>(null)
  const seen = useRef<number | null>(null)
  const [perm, setPerm] = useState(typeof Notification !== 'undefined' ? Notification.permission : 'unsupported')

  // Pop a notification when a new offer arrives
  useEffect(() => {
    const latest = data?.notifications?.[0]
    if (!latest) return
    if (seen.current === null) { seen.current = latest.id; return }
    if (latest.id !== seen.current) {
      seen.current = latest.id
      setToast(latest)
      setTimeout(() => setToast(null), 7000)
      if (perm === 'granted') new Notification(latest.title, { body: latest.body })
    }
  }, [data, perm])

  const reserve = async (l: any) => {
    setErr(null)
    try {
      const r = await api(`/listings/${l.id}/claim`, { body: { qty: 1 } })
      setCodes((c) => ({ ...c, [l.id]: r.claim.pickup_code }))
      refetch()
    } catch (e: any) {
      setErr(e.message)
    }
  }

  return (
    <div className="min-h-screen bg-slate-200 flex justify-center">
      <div className="w-full max-w-[420px] min-h-screen bg-slate-50 shadow-xl relative">
        <header className="bg-[#7a1f2b] text-white px-5 pt-6 pb-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs uppercase tracking-wider text-white/70">St Edmund Hall</div>
              <div className="text-2xl font-extrabold">Hall leftovers</div>
            </div>
            {perm === 'default' && (
              <button className="rounded-full bg-white/15 px-3 py-1.5 text-sm flex items-center gap-1"
                onClick={async () => setPerm(await Notification.requestPermission())}>
                <Bell size={14} /> Alerts
              </button>
            )}
          </div>
          <p className="text-sm text-white/80 mt-2">Good food the kitchen would otherwise throw away. First come, first served.</p>
        </header>

        {toast && (
          <div className="absolute left-3 right-3 top-3 z-10 rounded-2xl bg-white shadow-2xl border border-slate-200 p-4 animate-[slidein_.3s_ease-out]">
            <div className="font-bold">{toast.title}</div>
            <div className="text-sm text-slate-600 mt-0.5">{toast.body}</div>
          </div>
        )}

        <main className="p-4 space-y-3">
          {err && <div className="rounded-xl bg-red-50 text-red-700 text-sm p-3">{err}</div>}
          {data?.listings?.length === 0 && (
            <div className="text-center text-slate-500 py-16">Nothing right now. We'll ping you when food is available.</div>
          )}
          {data?.listings?.map((l: any) => {
            const free = l.price === 0
            const left = minsLeft(l.available_until)
            const code = codes[l.id]
            return (
              <div key={l.id} className="rounded-2xl bg-white shadow-sm border border-slate-200 overflow-hidden">
                <div className="flex gap-3 p-4">
                  <div className="text-5xl">{l.emoji}</div>
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-lg leading-tight">{l.title}</div>
                    <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
                      <span className="flex items-center gap-1"><MapPin size={12} />{l.location}</span>
                      <span className="flex items-center gap-1"><Clock size={12} />{left >= 60 ? `${Math.floor(left / 60)}h ${left % 60}m` : `${left} min`} left</span>
                    </div>
                    {l.allergens?.length > 0 && <div className="text-[11px] text-slate-400 mt-1">Contains: {l.allergens.join(', ')}</div>}
                  </div>
                  <div className="text-right">
                    <div className={`text-xl font-extrabold ${free ? 'text-leaf' : 'text-slate-900'}`}>{free ? 'FREE' : gbp(l.price)}</div>
                    {!free && l.normal_price && <div className="text-xs text-slate-400 line-through">{gbp(l.normal_price)}</div>}
                  </div>
                </div>
                <div className="px-4 pb-4 flex items-center gap-3">
                  <div className="flex-1">
                    <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                      <div className="h-full bg-leaf" style={{ width: `${(100 * l.qty_remaining) / l.qty}%` }} />
                    </div>
                    <div className="text-xs text-slate-500 mt-1">{l.qty_remaining} of {l.qty} left</div>
                  </div>
                  {code ? (
                    <div className="rounded-xl bg-leaf-50 text-leaf-600 px-4 py-2 font-bold">Pickup code {code}</div>
                  ) : (
                    <button onClick={() => reserve(l)} className="btn-green">Reserve</button>
                  )}
                </div>
              </div>
            )
          })}

          {data?.notifications?.length > 0 && (
            <div className="pt-4">
              <div className="label mb-2">Recent alerts</div>
              <ul className="space-y-2">
                {data.notifications.slice(0, 5).map((n: any) => (
                  <li key={n.id} className="text-sm bg-white rounded-xl p-3 border border-slate-200">
                    <span className="font-semibold">{n.title}</span>
                    <div className="text-slate-500">{n.body}</div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
