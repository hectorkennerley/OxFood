import { ArrowLeftRight, Boxes, ChefHat, PackageCheck, Recycle, ShoppingCart, Trash2, Truck } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useApi } from '../api'

const KIND: Record<string, { icon: any; colour: string }> = {
  order: { icon: ShoppingCart, colour: 'bg-ox' },
  transfer: { icon: ArrowLeftRight, colour: 'bg-leaf' },
  delivery: { icon: Truck, colour: 'bg-ox' },
  storage: { icon: Boxes, colour: 'bg-ox-600' },
  cooked: { icon: ChefHat, colour: 'bg-amberx' },
  recovered: { icon: Recycle, colour: 'bg-leaf' },
  waste: { icon: Trash2, colour: 'bg-red-500' },
}

export default function Journey() {
  const { lotId } = useParams()
  const nav = useNavigate()
  const { data: inv } = useApi<any>('/inventory', 0)
  const { data: j } = useApi<any>(lotId ? `/journey/${lotId}` : null, 4000)
  const lots = inv?.lots ?? []

  return (
    <div className="space-y-6 max-w-[1100px]">
      <div>
        <h1 className="h1">Food journey</h1>
        <p className="text-slate-500">Follow one batch through the ontology: supplier → order → delivery → storage → recipe → service → student or bin.</p>
      </div>
      <select className="input max-w-xl" value={lotId ?? ''} onChange={(e) => nav(`/journey/${e.target.value}`)}>
        <option value="">Choose a batch…</option>
        {lots.map((l: any) => <option key={l.id} value={l.id}>#{l.id} {l.product} ({l.qty} packs, use by {l.expiry_date}){l.source === 'transfer' ? ' · from marketplace' : ''}</option>)}
      </select>
      {j && (
        <div className="card p-6">
          <div className="flex items-center gap-3">
            <PackageCheck className="text-ox" />
            <div className="flex-1">
              <div className="font-bold text-lg">{j.product.name} · batch #{j.lot.id}</div>
              <div className="text-sm text-slate-500">{j.supplier} → {j.college} · status: {j.status.replace('_', ' ')}</div>
            </div>
          </div>
          <ol className="mt-6 relative border-l-2 border-slate-200 ml-4 space-y-5">
            {j.steps.map((s: any, i: number) => {
              const k = KIND[s.kind] ?? KIND.storage
              const Icon = k.icon
              return (
                <li key={i} className="ml-6">
                  <span className={`absolute -left-[17px] grid place-items-center h-8 w-8 rounded-full text-white ${k.colour}`}><Icon size={15} /></span>
                  <div className="text-xs text-slate-400">{new Date(s.when).toLocaleString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</div>
                  <div className={`font-semibold ${s.issue ? 'text-red-700' : ''}`}>{s.title}</div>
                  <div className="text-sm text-slate-600">{s.detail}</div>
                </li>
              )
            })}
          </ol>
        </div>
      )}
      {!lotId && <p className="text-sm text-slate-500">Tip: click any alert on the <Link to="/" className="underline">dashboard</Link> to jump to that batch.</p>}
    </div>
  )
}
