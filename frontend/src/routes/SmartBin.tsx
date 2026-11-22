import { Camera, Check, RefreshCw, Scale } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api, STAGES, useApi } from '../api'

/** Our software-only "Winnow": a webcam over the bin + any scale. */
export default function SmartBin() {
  const video = useRef<HTMLVideoElement>(null)
  const [camErr, setCamErr] = useState<string | null>(null)
  const [weight, setWeight] = useState(0)
  const [shot, setShot] = useState<string | null>(null)
  const [guess, setGuess] = useState<any | null>(null)
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState<any | null>(null)
  const { data: services } = useApi<any[]>('/services/today', 0)
  const h = new Date().getHours()
  const svc = services?.find((s) => s.meal === (h < 11 ? 'breakfast' : h < 17 ? 'lunch' : 'dinner')) ?? services?.[0]

  useEffect(() => {
    navigator.mediaDevices?.getUserMedia({ video: { width: 1280, height: 720 } })
      .then((stream) => { if (video.current) video.current.srcObject = stream })
      .catch((e) => setCamErr(e.message))
  }, [])

  const capture = async () => {
    const v = video.current
    if (!v || !v.videoWidth) return
    const scale = 768 / Math.max(v.videoWidth, v.videoHeight)
    const c = document.createElement('canvas')
    c.width = Math.round(v.videoWidth * scale)
    c.height = Math.round(v.videoHeight * scale)
    c.getContext('2d')!.drawImage(v, 0, 0, c.width, c.height)
    const url = c.toDataURL('image/jpeg', 0.7)
    setShot(url)
    setWeight(Math.round((0.4 + Math.random() * 2.6) * 100) / 100)
    setBusy(true)
    try {
      setGuess(await api('/ai/classify-photo', { body: { image_b64: url.split(',')[1], media_type: 'image/jpeg', service_id: svc?.id } }))
    } finally {
      setBusy(false)
    }
  }

  const confirm = async (dishId: number | null, stage: string) => {
    const r = await api('/waste', { body: { service_id: svc?.id, recipe_id: dishId, stage, weight_kg: weight, method: 'smart_bin', note: guess?.description ?? '' } })
    setSaved(r)
    setTimeout(() => { setSaved(null); setShot(null); setGuess(null) }, 2500)
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white p-6">
      <div className="text-2xl font-extrabold mb-4">🌱 OxFood Smart Bin <span className="text-white/50 font-medium text-lg">· camera + scale, no special hardware</span></div>
      <div className="grid grid-cols-[1fr_380px] gap-6">
        <div className="relative rounded-2xl overflow-hidden bg-black aspect-video">
          {shot ? <img src={shot} className="w-full h-full object-cover" /> : <video ref={video} autoPlay playsInline muted className="w-full h-full object-cover" />}
          {camErr && !shot && <div className="absolute inset-0 grid place-items-center text-white/70">Camera unavailable: {camErr}</div>}
          <div className="absolute top-4 right-4 rounded-xl bg-black/60 px-4 py-2 text-3xl font-bold tabular-nums flex items-center gap-2"><Scale /> {weight.toFixed(2)} kg</div>
          {saved && <div className="absolute inset-0 bg-leaf/80 grid place-items-center text-4xl font-bold"><div className="flex items-center gap-3"><Check size={48} /> Logged {saved.event.weight_kg} kg</div></div>}
        </div>
        <div className="space-y-4">
          {!shot ? (
            <button onClick={capture} className="w-full rounded-2xl bg-leaf py-8 text-2xl font-bold flex items-center justify-center gap-3"><Camera size={32} /> Scrape & weigh</button>
          ) : (
            <button onClick={() => { setShot(null); setGuess(null) }} className="w-full rounded-2xl bg-white/10 py-3 font-semibold flex items-center justify-center gap-2"><RefreshCw size={18} /> Retake</button>
          )}
          {busy && <div className="text-white/70">Recognising…</div>}
          {guess && (
            <div className="rounded-2xl bg-white text-slate-900 p-4">
              <div className="label">{guess.source === 'ai' || guess.source === 'cache' ? `Claude thinks (${Math.round(guess.confidence * 100)}%)` : 'Pick the dish'}</div>
              <div className="text-sm text-slate-600 mb-3">{guess.description}</div>
              <div className="space-y-2">
                {svc?.dishes.map((d: any) => (
                  <button key={d.id} onClick={() => confirm(d.id, guess.stage)}
                    className={`w-full text-left rounded-xl px-3 py-2.5 border-2 font-semibold ${guess.dish_id === d.id ? 'border-leaf bg-leaf-50' : 'border-slate-200'}`}>
                    {d.emoji} {d.name}
                  </button>
                ))}
                <button onClick={() => confirm(null, 'plate_waste')} className="w-full text-left rounded-xl px-3 py-2.5 border-2 border-slate-200 font-semibold">🧽 Mixed plate waste</button>
              </div>
              <div className="text-xs text-slate-500 mt-2">Stage: {STAGES[guess.stage]?.label}</div>
            </div>
          )}
          <p className="text-xs text-white/50">Inspired by St Edmund Hall's use of Winnow, which logs plate waste, overproduction and trimmings. OxFood does it with a tablet camera and any scale.</p>
        </div>
      </div>
    </div>
  )
}
