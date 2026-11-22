import { Check, Delete, Mic, Scale, ShieldAlert, Sparkles, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { api, DISPOSITION, gbp, useAction, useApi } from '../api'
import en from '../i18n/en.json'
import es from '../i18n/es.json'
import fr from '../i18n/fr.json'

const LANGS = { en: { t: en, speech: 'en-GB', flag: '🇬🇧' }, fr: { t: fr, speech: 'fr-FR', flag: '🇫🇷' }, es: { t: es, speech: 'es-ES', flag: '🇪🇸' } }
type Lang = keyof typeof LANGS

/** Waste stages a chef can pick, based on the dish's recipe stages. */
function stagesFor(dish: any | null): string[] {
  if (!dish) return ['plate_waste', 'prep_trim', 'spoilage']
  const s: string[] = dish.stages
  const out: string[] = []
  if (s.includes('cook') || s.includes('chill') || s.includes('hot_hold')) out.push('overproduction')
  if (s.includes('servery')) out.push('servery_leftover')
  out.push('plate_waste')
  if (s.includes('prep')) out.push('prep_trim')
  if (s.includes('cook')) out.push('cooking_error')
  return out
}

function defaultMeal() {
  const h = new Date().getHours()
  return h < 11 ? 'breakfast' : h < 17 ? 'lunch' : 'dinner'
}

export default function TabletApp() {
  const [lang, setLang] = useState<Lang>(() => (localStorageGet('oxfood.lang') as Lang) || 'en')
  const t = LANGS[lang].t as Record<string, string>
  const { data: services } = useApi<any[]>('/services/today', 10000)
  const [meal, setMeal] = useState(defaultMeal())
  const svc = services?.find((s) => s.meal === meal) ?? services?.[0]
  const [dishId, setDishId] = useState<number | null>(null)
  const [stage, setStage] = useState<string | null>(null)
  const [amount, setAmount] = useState('')
  const [unit, setUnit] = useState<'kg' | 'portions'>('kg')
  const [method, setMethod] = useState('tablet')
  const [note, setNote] = useState('')
  const [result, setResult] = useState<any | null>(null)
  const [aiSource, setAiSource] = useState<string | null>(null)
  const save = useAction('/waste')
  const recent = useApi<any[]>('/waste/recent', 4000)

  const dish = svc?.dishes.find((d: any) => d.id === dishId) ?? null
  const stages = stagesFor(dish)

  useEffect(() => { if (stage && !stages.includes(stage)) setStage(null) }, [dishId]) // eslint-disable-line

  const reset = () => { setDishId(null); setStage(null); setAmount(''); setUnit('kg'); setResult(null); setMethod('tablet'); setNote(''); setAiSource(null) }

  const submit = async () => {
    const n = parseFloat(amount)
    if (!stage || !n) return
    const r = await save.mutateAsync({
      service_id: svc?.id, recipe_id: dishId, stage, method, note,
      ...(unit === 'kg' ? { weight_kg: n } : { portions: Math.round(n) }),
    })
    setResult(r)
  }

  const applyParse = (p: any) => {
    setDishId(p.dish_id ?? null)
    setStage(p.stage)
    if (p.weight_kg) { setAmount(String(p.weight_kg)); setUnit('kg') } else if (p.portions) { setAmount(String(p.portions)); setUnit('portions') }
    setMethod('voice')
    setNote(p.note ?? '')
    setAiSource(p.source)
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 select-none">
      <header className="bg-ox text-white px-6 py-4 flex items-center gap-4">
        <div className="text-2xl font-extrabold">🌱 OxFood <span className="font-medium text-white/70">Kitchen</span></div>
        <div className="flex gap-2 ml-6">
          {(['breakfast', 'lunch', 'dinner'] as const).map((m) => (
            <button key={m} onClick={() => { setMeal(m); reset() }}
              className={`rounded-xl px-5 py-2.5 text-lg font-semibold ${meal === m ? 'bg-white text-ox' : 'bg-white/10'}`}>{t[m]}</button>
          ))}
        </div>
        <div className="ml-auto flex gap-1">
          {(Object.keys(LANGS) as Lang[]).map((l) => (
            <button key={l} onClick={() => { setLang(l); localStorageSet('oxfood.lang', l) }}
              className={`text-2xl rounded-lg px-2 py-1 ${lang === l ? 'bg-white/25' : 'opacity-60'}`}>{LANGS[l].flag}</button>
          ))}
        </div>
      </header>

      <div className="p-6 grid grid-cols-[1fr_340px] gap-6">
        <div className="space-y-6">
          {result ? (
            <ResultPanel result={result} t={t} onDone={reset} />
          ) : (
            <>
              <VoiceBar t={t} lang={lang} serviceId={svc?.id} onParsed={applyParse} />
              {aiSource && (
                <div className="flex items-center gap-2 text-sm text-leaf-600 font-semibold">
                  <Sparkles size={16} /> {t.confirm_voice} · {aiSource === 'ai' || aiSource === 'cache' ? 'understood by Claude' : 'understood by keyword rules'}
                </div>
              )}
              <section>
                <div className="text-lg font-bold mb-3">{t.pick_dish}</div>
                <div className="grid grid-cols-3 gap-3">
                  {svc?.dishes.map((d: any) => (
                    <button key={d.id} onClick={() => setDishId(d.id)}
                      className={`card p-4 text-left min-h-[110px] border-2 ${dishId === d.id ? 'border-ox ring-4 ring-ox-100' : 'border-transparent'}`}>
                      <div className="text-4xl">{d.emoji}</div>
                      <div className="mt-2 text-lg font-semibold leading-tight">{d.name}</div>
                    </button>
                  ))}
                  <button onClick={() => { setDishId(null); setStage('plate_waste') }}
                    className={`card p-4 text-left min-h-[110px] border-2 ${dishId === null && stage === 'plate_waste' ? 'border-ox ring-4 ring-ox-100' : 'border-transparent'}`}>
                    <div className="text-4xl">🧽</div>
                    <div className="mt-2 text-lg font-semibold leading-tight">{t.plate_waste_any}</div>
                  </button>
                </div>
              </section>
              <section>
                <div className="text-lg font-bold mb-3">{t.pick_stage}</div>
                <div className="flex flex-wrap gap-3">
                  {stages.map((s) => (
                    <button key={s} onClick={() => setStage(s)}
                      className={`rounded-2xl px-5 py-4 text-lg font-semibold border-2 ${stage === s ? 'bg-ox text-white border-ox' : 'bg-white border-slate-200'}`}>
                      {t[`stage_${s}`]}
                    </button>
                  ))}
                </div>
              </section>
            </>
          )}
        </div>

        {!result && (
          <aside className="space-y-4">
            <div className="card p-4">
              <div className="text-lg font-bold mb-2">{t.weight}</div>
              <div className="flex gap-2 mb-3">
                {(['kg', 'portions'] as const).map((u) => (
                  <button key={u} onClick={() => setUnit(u)}
                    className={`flex-1 rounded-xl py-2 font-semibold ${unit === u ? 'bg-ox text-white' : 'bg-slate-100'}`}>{t[u]}</button>
                ))}
              </div>
              <div className="rounded-xl bg-slate-900 text-white text-right px-4 py-3 text-5xl font-bold tabular-nums h-[76px]">
                {amount || '0'}<span className="text-xl text-white/60 ml-2">{t[unit]}</span>
              </div>
              <Keypad value={amount} onChange={setAmount} />
              <button className="btn-ghost w-full mt-2 py-3 text-lg"
                onClick={() => { setUnit('kg'); setAmount((Math.round((1.5 + Math.random() * 3.5) * 10) / 10).toString()); setMethod('scale') }}>
                <Scale size={20} /> {t.read_scale}
              </button>
            </div>
            <button disabled={!stage || !parseFloat(amount) || save.isPending} onClick={submit}
              className="btn-green w-full py-5 text-2xl rounded-2xl">
              <Check size={28} /> {t.save}
            </button>
            {save.error && <div className="text-red-600 text-sm">{save.error.message}</div>}
            <Recent rows={recent.data ?? []} t={t} />
          </aside>
        )}
      </div>
    </div>
  )
}

function Keypad({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const press = (k: string) => {
    if (k === 'del') return onChange(value.slice(0, -1))
    if (k === '.' && value.includes('.')) return
    if (value.length >= 5) return
    onChange(value === '0' && k !== '.' ? k : value + k)
  }
  return (
    <div className="grid grid-cols-3 gap-2 mt-3">
      {['1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '0', 'del'].map((k) => (
        <button key={k} onClick={() => press(k)} className="rounded-xl bg-slate-100 py-3.5 text-2xl font-semibold active:bg-slate-200">
          {k === 'del' ? <Delete className="mx-auto" /> : k}
        </button>
      ))}
    </div>
  )
}

function VoiceBar({ t, lang, serviceId, onParsed }: { t: Record<string, string>; lang: Lang; serviceId?: number; onParsed: (p: any) => void }) {
  const [listening, setListening] = useState(false)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const recRef = useRef<any>(null)
  const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

  const parse = async (transcript: string) => {
    if (!transcript.trim()) return
    setBusy(true)
    try {
      onParsed(await api('/ai/parse-waste', { body: { transcript, service_id: serviceId } }))
    } finally {
      setBusy(false)
    }
  }

  const start = () => {
    if (!SR) return
    const rec = new SR()
    rec.lang = LANGS[lang].speech
    rec.interimResults = true
    rec.onresult = (e: any) => setText(Array.from(e.results).map((r: any) => r[0].transcript).join(' '))
    rec.onend = () => setListening(false)
    rec.start()
    recRef.current = rec
    setText('')
    setListening(true)
  }
  const stop = () => {
    recRef.current?.stop()
    setListening(false)
    setTimeout(() => setText((cur) => { parse(cur); return cur }), 300)
  }

  return (
    <div className="card p-4 flex items-center gap-4">
      <button
        onPointerDown={start} onPointerUp={stop} onPointerLeave={() => listening && stop()} disabled={!SR || busy}
        className={`shrink-0 h-20 w-20 rounded-full grid place-items-center text-white transition ${listening ? 'bg-red-500 scale-110 animate-pulse' : 'bg-ox'}`}
        title={SR ? t.hold_to_speak : 'Speech recognition needs Chrome'}>
        <Mic size={36} />
      </button>
      <div className="flex-1">
        <div className="font-semibold text-lg">{listening ? t.listening : t.hold_to_speak}</div>
        <form onSubmit={(e) => { e.preventDefault(); parse(text) }} className="flex gap-2 mt-1">
          <input className="input text-lg" value={text} onChange={(e) => setText(e.target.value)}
            placeholder={`${t.or_type}: "3 kilos of curry never left the kitchen"`} />
          <button className="btn-primary" disabled={busy || !text.trim()}>{busy ? '…' : <Sparkles size={18} />}</button>
        </form>
      </div>
    </div>
  )
}

function ResultPanel({ result, t, onDone }: { result: any; t: Record<string, string>; onDone: () => void }) {
  const ev = result.event
  const adv = result.advice
  const canOffer = adv.options.some((o: any) => o.disposition === 'offer_students') && result.offer.portions > 0
  const [portions, setPortions] = useState(result.offer.portions)
  const [price, setPrice] = useState(result.offer.suggested_price)
  const [sent, setSent] = useState<string | null>(null)
  const offer = useAction('/listings/offer')
  const dispose = useAction<{ disposition: string }>(`/waste/${ev.id}/disposition`)

  const chosen = useMemo(() => sent, [sent])
  return (
    <div className="space-y-5">
      <div className="card p-5 flex items-center gap-4 border-leaf border-2">
        <div className="h-14 w-14 rounded-full bg-leaf text-white grid place-items-center"><Check size={32} /></div>
        <div>
          <div className="text-2xl font-bold">{t.saved}: {ev.weight_kg} kg{result.offer.dish ? ` · ${result.offer.dish}` : ''}</div>
          <div className="text-slate-500">≈ {ev.portions_est} {t.portions} · {gbp(ev.value_gbp)} of food</div>
        </div>
      </div>

      <div className="text-xl font-bold">{t.what_now}</div>
      {canOffer && !chosen && (
        <div className="card p-5 border-2 border-leaf bg-leaf-50">
          <div className="text-xl font-bold text-leaf-600">🍽️ {t.offer}</div>
          <div className="flex items-center gap-3 mt-3 text-xl">
            <Stepper value={portions} onChange={setPortions} min={1} max={200} />
            <span>{t.portions} {t.at}</span>
            <Stepper value={price} onChange={setPrice} min={0} max={20} step={0.5} money />
            <span className="text-slate-500 text-base">{t.each} (normally {gbp(result.offer.normal_price)})</span>
          </div>
          <button className="btn-green w-full mt-4 py-4 text-xl" disabled={offer.isPending}
            onClick={async () => { await offer.mutateAsync({ waste_event_id: ev.id, portions, price }); setSent('offer_students') }}>
            {t.send_offer} 📣
          </button>
        </div>
      )}
      {chosen && (
        <div className="card p-5 bg-leaf-50 border-leaf border-2 text-xl font-semibold text-leaf-600">
          ✅ {DISPOSITION[chosen]}{chosen === 'offer_students' ? ` · ${portions} × ${gbp(price)}` : ''}
        </div>
      )}

      {!chosen && (
        <div className="grid grid-cols-2 gap-3">
          {adv.options.filter((o: any) => o.disposition !== 'offer_students').map((o: any) => (
            <button key={o.disposition} onClick={async () => { await dispose.mutateAsync({ disposition: o.disposition }); setSent(o.disposition) }}
              className={`card p-4 text-left border-2 ${o.recommended ? 'border-ox' : 'border-transparent'}`}>
              <div className="font-bold text-lg">{o.label}</div>
              <div className="text-sm text-slate-600 mt-1">{o.reason}</div>
            </button>
          ))}
        </div>
      )}

      {adv.blocked.length > 0 && (
        <div className="card p-4 bg-red-50 border-red-200">
          <div className="flex items-center gap-2 font-bold text-red-700"><ShieldAlert size={18} /> {t.not_allowed}</div>
          <ul className="mt-1 text-red-800 text-sm list-disc ml-5">{adv.blocked.map((b: string) => <li key={b}>{b}</li>)}</ul>
        </div>
      )}
      {result.tip && <div className="text-sm text-slate-600">💡 {result.tip}</div>}
      <div className="text-xs text-slate-400">{adv.disclaimer}</div>
      <button onClick={onDone} className="btn-primary w-full py-4 text-xl">{t.done}</button>
    </div>
  )
}

function Stepper({ value, onChange, min, max, step = 1, money }: { value: number; onChange: (n: number) => void; min: number; max: number; step?: number; money?: boolean }) {
  const set = (n: number) => onChange(Math.min(max, Math.max(min, Math.round(n * 100) / 100)))
  return (
    <div className="flex items-center rounded-xl bg-white border border-slate-300 overflow-hidden">
      <button className="px-4 py-2 text-2xl" onClick={() => set(value - step)}>−</button>
      <div className="px-3 font-bold tabular-nums min-w-[70px] text-center">{money ? (value === 0 ? 'FREE' : gbp(value)) : value}</div>
      <button className="px-4 py-2 text-2xl" onClick={() => set(value + step)}>+</button>
    </div>
  )
}

function Recent({ rows, t }: { rows: any[]; t: Record<string, string> }) {
  if (!rows.length) return null
  return (
    <div className="card p-4">
      <div className="font-bold mb-2">{t.recent}</div>
      <ul className="space-y-1.5 text-sm">
        {rows.slice(0, 6).map((r) => (
          <li key={r.id} className="flex items-center gap-2">
            <span>{r.emoji}</span>
            <span className="flex-1 truncate">{r.dish ?? t[`stage_${r.stage}`]}</span>
            <span className="font-semibold">{r.weight_kg} kg</span>
            {r.disposition !== 'pending' ? <span className="chip bg-leaf-50 text-leaf-600">{DISPOSITION[r.disposition]?.split(' ')[0]}</span> : <X size={14} className="text-slate-300" />}
          </li>
        ))}
      </ul>
    </div>
  )
}

function localStorageGet(k: string) {
  try { return localStorage.getItem(k) } catch { return null }
}
function localStorageSet(k: string, v: string) {
  try { localStorage.setItem(k, v) } catch { /* private mode */ }
}
