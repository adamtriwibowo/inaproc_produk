import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { AlertTriangle, CheckCircle2, Info, Loader2, X, XCircle } from 'lucide-react'

export const Spinner = ({ className = '' }) => <Loader2 className={`h-4 w-4 animate-spin ${className}`} aria-hidden />

export function Loading({ text = 'Memuat…' }) {
  return (
    <div className="flex items-center gap-2 p-6 text-sm text-muted-fg" role="status">
      <Spinner /> {text}
    </div>
  )
}

export function ErrorBox({ error }) {
  if (!error) return null
  const list = Array.isArray(error.detail?.detail) ? error.detail.detail : null
  return (
    <div role="alert" className="flex items-start gap-2 rounded-md border border-bad/30 bg-bad-bg p-3 text-sm text-bad">
      <XCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div>
        {error.message || String(error)}
        {list && <ul className="mt-1 list-disc pl-5">{list.map((x, i) => <li key={i}>{x}</li>)}</ul>}
      </div>
    </div>
  )
}

const TONES = {
  ok: 'bg-ok-bg text-ok', warn: 'bg-warn-bg text-warn', bad: 'bg-bad-bg text-bad',
  info: 'bg-primary/10 text-primary', mute: 'bg-muted text-muted-fg',
}
const TONE_ICON = { ok: CheckCircle2, warn: AlertTriangle, bad: XCircle, info: Info }

/** Status selalu memakai ikon + teks, tidak hanya warna. */
export function Chip({ tone = 'mute', children, icon = true }) {
  const I = TONE_ICON[tone]
  return (
    <span className={`chip ${TONES[tone]}`}>
      {icon && I && <I className="h-3 w-3" aria-hidden />}
      {children}
    </span>
  )
}

export function statusTone(s) {
  return {
    Bisa: 'ok', Sebagian: 'warn', 'Tidak Bisa': 'bad', Draft: 'mute', Diajukan: 'info', 'Perlu Perbaikan': 'warn',
    Disetujui: 'ok', Diekspor: 'info', 'Sudah Diunggah': 'ok',
  }[s] || 'mute'
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold">{title}</h1>
        {subtitle && <p className="mt-0.5 text-sm text-muted-fg">{subtitle}</p>}
      </div>
      <div className="flex flex-wrap gap-2">{actions}</div>
    </div>
  )
}

export function Modal({ title, onClose, children, wide }) {
  const ref = useRef(null)
  useEffect(() => {
    const prev = document.activeElement
    ref.current?.focus()
    const k = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', k)
    return () => { window.removeEventListener('keydown', k); prev?.focus?.() }
  }, [onClose])
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4" onMouseDown={onClose}>
      <div
        ref={ref} tabIndex={-1} role="dialog" aria-modal="true" aria-label={title}
        className={`card mt-10 w-full ${wide ? 'max-w-3xl' : 'max-w-lg'} p-5 shadow-lg`}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button className="btn btn-sm" onClick={onClose} aria-label="Tutup"><X className="h-4 w-4" /></button>
        </div>
        {children}
      </div>
    </div>
  )
}

const ToastCtx = createContext(() => {})
export const useToast = () => useContext(ToastCtx)

export function ToastProvider({ children }) {
  const [items, setItems] = useState([])
  const push = useCallback((msg, tone = 'ok') => {
    const id = Math.random()
    setItems((x) => [...x, { id, msg, tone }])
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), 4500)
  }, [])
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-[60] flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2" aria-live="polite">
        {items.map((i) => (
          <div key={i.id} className={`card flex items-start gap-2 p-3 text-sm shadow-md ${i.tone === 'bad' ? 'border-bad/40' : ''}`}>
            {i.tone === 'bad' ? <XCircle className="h-4 w-4 shrink-0 text-bad" /> : <CheckCircle2 className="h-4 w-4 shrink-0 text-ok" />}
            <span>{i.msg}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

export function Empty({ children }) {
  return <div className="p-8 text-center text-sm text-muted-fg">{children}</div>
}

export function Stat({ label, value, tone = 'mute', hint }) {
  const c = { ok: 'text-ok', bad: 'text-bad', warn: 'text-warn' }[tone] || ''
  return (
    <div className="card p-3">
      <div className="text-xs font-medium text-muted-fg">{label}</div>
      <div className={`mt-1 font-mono text-2xl font-semibold ${c}`}>{value}</div>
      {hint && <div className="mt-0.5 text-xs text-muted-fg">{hint}</div>}
    </div>
  )
}

/** Hook sederhana pemuat data. */
export function useLoad(fn, deps) {
  const [state, set] = useState({ data: null, error: null, loading: true })
  const reload = useCallback(async () => {
    set((s) => ({ ...s, loading: true, error: null }))
    try { set({ data: await fn(), error: null, loading: false }) } catch (e) { set({ data: null, error: e, loading: false }) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  useEffect(() => { reload() }, [reload])
  return { ...state, reload }
}
