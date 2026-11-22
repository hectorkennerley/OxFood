import { CheckCircle2, Plus } from 'lucide-react'
import { useState } from 'react'
import { useAction, useApi } from '../api'

const ISSUE_TYPES = ['short', 'late', 'quality', 'substitution', 'temp_breach', 'damaged', 'wrong_item']

export default function Suppliers() {
  const { data: sups = [] } = useApi<any[]>('/suppliers', 5000)
  const { data: issues = [] } = useApi<any[]>('/suppliers/issues', 5000)
  const { data: products = [] } = useApi<any[]>('/catalogue', 0)
  const toggle = useAction<{ id: number; active: boolean }>((b) => `/suppliers/${b.id}/toggle`)
  const addSup = useAction('/suppliers')
  const addIssue = useAction('/suppliers/issues')
  const resolve = useAction<{ id: number }>((b) => `/suppliers/issues/${b.id}/resolve`)
  const [showAdd, setShowAdd] = useState(false)
  const [newSup, setNewSup] = useState({ name: '', code: '', category: 'produce' })
  const [issue, setIssue] = useState({ supplier_id: 0, type: 'short', product_id: 0, notes: '' })
  const [filter, setFilter] = useState<number | null>(null)

  const open = issues.filter((i) => !i.resolved)
  const shown = issues.filter((i) => filter == null || i.supplier_id === filter).slice(0, 25)

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="h1">Suppliers & distribution issues</h1>
          <p className="text-slate-500">Turn distributors on or off for your catalogue, and track what goes wrong.</p>
        </div>
        <button className="btn-primary" onClick={() => setShowAdd((s) => !s)}><Plus size={16} /> Add distributor</button>
      </div>

      {showAdd && (
        <div className="card p-4 flex gap-3 items-end">
          <div className="flex-1"><div className="label mb-1">Name</div><input className="input" value={newSup.name} onChange={(e) => setNewSup({ ...newSup, name: e.target.value })} /></div>
          <div className="w-32"><div className="label mb-1">Code</div><input className="input" value={newSup.code} onChange={(e) => setNewSup({ ...newSup, code: e.target.value })} /></div>
          <div className="w-40"><div className="label mb-1">Category</div>
            <select className="input" value={newSup.category} onChange={(e) => setNewSup({ ...newSup, category: e.target.value })}>
              {['produce', 'dairy', 'meat', 'bakery', 'dry', 'fish', 'frozen'].map((c) => <option key={c}>{c}</option>)}
            </select></div>
          <button className="btn-green" disabled={!newSup.name || !newSup.code}
            onClick={async () => { await addSup.mutateAsync(newSup); setShowAdd(false); setNewSup({ name: '', code: '', category: 'produce' }) }}>Save</button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {sups.map((s) => (
          <div key={s.id} className={`card p-4 ${!s.active ? 'opacity-60' : ''} ${filter === s.id ? 'ring-2 ring-ox' : ''}`}>
            <div className="flex items-start gap-2">
              <button className="flex-1 text-left" onClick={() => setFilter(filter === s.id ? null : s.id)}>
                <div className="font-bold">{s.name}</div>
                <div className="text-xs text-slate-500">{s.code} · {s.category} · {s.products} products · {s.lead_time_days}d lead time</div>
              </button>
              <label className="flex items-center gap-1 text-xs cursor-pointer">
                <input type="checkbox" checked={s.active} onChange={(e) => toggle.mutate({ id: s.id, active: e.target.checked })} />
                {s.active ? 'Active' : 'Off'}
              </label>
            </div>
            <div className="mt-3 flex items-end gap-3">
              <div>
                <div className={`text-3xl font-bold ${s.reliability >= 90 ? 'text-leaf-600' : s.reliability >= 80 ? 'text-amberx' : 'text-red-600'}`}>{s.reliability}%</div>
                <div className="label">reliability</div>
              </div>
              <div className="flex-1 flex flex-wrap gap-1 justify-end">
                {Object.entries(s.issue_types).slice(0, 3).map(([t, n]) => (
                  <span key={t} className="chip bg-slate-100 text-slate-700">{t.replace('_', ' ')} ×{n as number}</span>
                ))}
              </div>
            </div>
            {s.open_issues > 0 && <div className="text-xs text-red-600 font-semibold mt-2">{s.open_issues} open issue(s)</div>}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-6">
        <div className="card p-5">
          <div className="font-bold mb-3">{filter ? `Issues: ${sups.find((s) => s.id === filter)?.name}` : 'Issue log'} <span className="text-slate-400 font-normal">({open.length} open)</span></div>
          <div className="space-y-3">
            {shown.map((i) => (
              <div key={i.id} className={`rounded-xl border p-3 ${i.resolved ? 'border-slate-200' : 'border-red-300 bg-red-50/50'}`}>
                <div className="flex items-center gap-2 text-sm">
                  <span className="chip bg-ox-50 text-ox">{i.type.replace('_', ' ')}</span>
                  <span className="font-semibold">{i.supplier}</span>
                  <span className="text-slate-500">{i.date}</span>
                  {i.product && <span className="text-slate-600">· {i.product}</span>}
                  {i.substitute && <span className="text-slate-600">→ substituted with {i.substitute}</span>}
                  <span className="flex-1" />
                  {i.resolved ? <CheckCircle2 size={16} className="text-leaf" /> : <button className="btn-ghost !py-1 !px-2 text-xs" onClick={() => resolve.mutate({ id: i.id })}>Resolve</button>}
                </div>
                <div className="text-sm text-slate-600 mt-1">{i.notes}</div>
                {!i.resolved && (
                  <ul className="mt-2 text-sm list-disc ml-5 text-slate-700">
                    {i.recovery.map((r: string) => <li key={r}>{r}</li>)}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </div>
        <div className="card p-5 h-fit">
          <div className="font-bold mb-3">Report a delivery issue</div>
          <div className="space-y-3">
            <select className="input" value={issue.supplier_id} onChange={(e) => setIssue({ ...issue, supplier_id: +e.target.value })}>
              <option value={0}>Supplier…</option>
              {sups.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <div className="flex flex-wrap gap-2">
              {ISSUE_TYPES.map((t) => (
                <button key={t} onClick={() => setIssue({ ...issue, type: t })} className={`chip !py-1.5 !px-3 ${issue.type === t ? 'bg-ox text-white' : 'bg-slate-100'}`}>{t.replace('_', ' ')}</button>
              ))}
            </div>
            <select className="input" value={issue.product_id} onChange={(e) => setIssue({ ...issue, product_id: +e.target.value })}>
              <option value={0}>Product (optional)…</option>
              {products.filter((p) => !issue.supplier_id || p.supplier_id === issue.supplier_id).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <textarea className="input" rows={2} placeholder="What happened?" value={issue.notes} onChange={(e) => setIssue({ ...issue, notes: e.target.value })} />
            <button className="btn-primary w-full" disabled={!issue.supplier_id}
              onClick={async () => { await addIssue.mutateAsync({ ...issue, product_id: issue.product_id || null }); setIssue({ supplier_id: 0, type: 'short', product_id: 0, notes: '' }) }}>
              Log issue & get recovery steps
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
