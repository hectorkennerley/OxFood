import { Sparkles } from 'lucide-react'
import { useState } from 'react'
import { gbp, useApi } from '../api'

export default function Menu() {
  const [meal, setMeal] = useState('lunch')
  const [useAi, setUseAi] = useState(false)
  const { data: s, isFetching } = useApi<any>(`/menu/suggestions?meal=${meal}&use_ai=${useAi}`, 0)
  const { data: recipes = [] } = useApi<any[]>('/recipes', 0)
  const [open, setOpen] = useState<number | null>(null)
  const aiPick = (id: number) => s?.ai?.picks?.find((p: any) => p.recipe_id === id)

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="h1">Menu planner</h1>
        <p className="text-slate-500">Tomorrow's dishes ranked by how much near-expiry stock and chilled leftovers they use up, checked against appliances and staff.</p>
      </div>
      <div className="flex items-center gap-2">
        {['breakfast', 'lunch', 'dinner'].map((m) => (
          <button key={m} className={`chip !py-2 !px-4 !text-sm ${meal === m ? 'bg-ox text-white' : 'bg-white border border-slate-200'}`} onClick={() => setMeal(m)}>{m}</button>
        ))}
        <span className="flex-1" />
        <button className={useAi ? 'btn-primary' : 'btn-ghost'} onClick={() => setUseAi((v) => !v)}>
          <Sparkles size={16} /> {useAi ? 'Claude rationale on' : 'Add Claude rationale'}
        </button>
      </div>
      {s && (
        <div className="card p-5">
          <div className="flex items-center gap-4">
            <div className="font-bold flex-1">Suggestions for {meal} on {new Date(s.date).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'short' })}</div>
            {s.forecast && <div className="text-sm text-slate-600">Forecast: cook <b>{s.forecast.recommended_portions}</b> · {s.staff_on_shift} staff</div>}
          </div>
          {s.ai?.summary && <div className="mt-3 rounded-xl bg-ox-50 p-3 text-sm text-ox"><Sparkles size={14} className="inline mr-1" />{s.ai.summary}</div>}
          {s.ai && !s.ai.summary && <div className="mt-3 text-xs text-slate-500">Claude unavailable ({s.ai.source}): showing the rule-based ranking.</div>}
          {isFetching && <div className="text-xs text-slate-400 mt-2">Updating…</div>}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3 mt-4">
            {s.candidates.map((c: any, i: number) => {
              const ap = aiPick(c.recipe_id)
              return (
                <div key={c.recipe_id} className={`rounded-2xl border p-4 ${i < 3 ? 'border-leaf bg-leaf-50/40' : 'border-slate-200'}`}>
                  <div className="text-3xl">{c.emoji}</div>
                  <div className="font-bold mt-1 leading-tight">{c.name}</div>
                  <div className="text-xs text-slate-500 mt-1">score {c.score} · cost {gbp(c.cost_per_portion)} · price {gbp(ap?.suggested_price ?? c.sell_price)}</div>
                  {c.uses_expiring.length > 0 && <div className="text-xs mt-2"><b>Uses up:</b> {c.uses_expiring.join(', ')}</div>}
                  {c.reasons.map((r: string) => <div key={r} className="text-xs text-slate-600 mt-1">• {r}</div>)}
                  {ap && <div className="text-xs text-ox mt-2">✨ {ap.why}</div>}
                </div>
              )
            })}
          </div>
        </div>
      )}
      <div className="card p-5">
        <div className="font-bold mb-3">Recipes and cooking stages</div>
        <div className="divide-y divide-slate-100">
          {recipes.map((r) => (
            <div key={r.id} className="py-2">
              <button className="w-full flex items-center gap-3 text-left" onClick={() => setOpen(open === r.id ? null : r.id)}>
                <span className="text-xl">{r.emoji}</span>
                <span className="font-medium flex-1">{r.name}</span>
                <span className="hidden md:flex gap-1">{r.stages.map((st: string) => <span key={st} className="chip bg-slate-100 text-slate-600">{st.replace('_', ' ')}</span>)}</span>
                <span className="text-sm tabular-nums w-28 text-right">{gbp(r.cost_per_portion)} → {gbp(r.sell_price)}</span>
              </button>
              {open === r.id && (
                <div className="ml-10 mt-2 text-sm text-slate-600 grid md:grid-cols-3 gap-2">
                  <div><div className="label">Ingredients / portion</div>{r.ingredients.map((i: any) => <div key={i.product_id}>{i.name}: {i.qty_per_portion} {i.unit}</div>)}</div>
                  <div><div className="label">Appliances</div>{r.appliances.join(', ') || 'none'}</div>
                  <div><div className="label">Allergens</div>{r.allergens.join(', ') || 'none'}{r.high_risk && <div className="text-amberx mt-1">High-risk (rice/seafood): 24h chill limit</div>}</div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
