import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

export const HOME = 1

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method: opts.method ?? (opts.body ? 'POST' : 'GET'),
    headers: opts.body ? { 'content-type': 'application/json' } : undefined,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  })
  if (!res.ok) {
    let msg = res.statusText
    try {
      const j = await res.json()
      msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
    } catch {
      /* ignore */
    }
    throw new Error(msg)
  }
  return res.json()
}

/** GET with polling (so separate browser windows stay in sync during the demo). */
export function useApi<T = any>(path: string | null, poll = 3000) {
  return useQuery<T>({
    queryKey: [path],
    queryFn: () => api<T>(path!),
    enabled: !!path,
    refetchInterval: poll || false,
  })
}

/** POST, then refresh everything (cheap at demo scale). */
export function useAction<TBody = any, TRes = any>(path: string | ((b: TBody) => string)) {
  const qc = useQueryClient()
  return useMutation<TRes, Error, TBody>({
    mutationFn: (body: TBody) => api<TRes>(typeof path === 'function' ? path(body) : path, { method: 'POST', body: body ?? {} }),
    onSuccess: () => qc.invalidateQueries(),
  })
}

export const gbp = (n: number | null | undefined, dp = 2) =>
  n == null ? '–' : `£${n.toLocaleString('en-GB', { minimumFractionDigits: dp, maximumFractionDigits: dp })}`

export const kg = (n: number | null | undefined) => (n == null ? '–' : `${n.toLocaleString('en-GB', { maximumFractionDigits: 1 })} kg`)

export const STAGES: Record<string, { label: string; emoji: string; colour: string }> = {
  overproduction: { label: 'Overproduced (never left kitchen)', emoji: '🍲', colour: '#0b3b73' },
  servery_leftover: { label: 'Servery leftover', emoji: '🍽️', colour: '#2f8f5b' },
  plate_waste: { label: 'Plate waste', emoji: '🧽', colour: '#c27c0e' },
  prep_trim: { label: 'Prep trim', emoji: '🔪', colour: '#7c3aed' },
  spoilage: { label: 'Spoiled stock', emoji: '🦠', colour: '#b91c1c' },
  cooking_error: { label: 'Burnt / dropped', emoji: '🔥', colour: '#64748b' },
}

export const DISPOSITION: Record<string, string> = {
  offer_students: 'Offered to students',
  chill_reuse: 'Blast-chilled for reuse',
  marketplace: 'Listed for colleges',
  donate: 'Donated',
  staff_meal: 'Stock / staff meal',
  compost: 'Composted',
  discard: 'Binned',
  pending: 'Awaiting decision',
  freeze: 'Frozen',
}
