import { useCallback, useEffect, useRef, useState } from 'react'
import { api, C } from './api.js'

/**
 * State baris batch + simpan otomatis (debounce). Setiap edit langsung terlihat; server mengembalikan
 * hasil validasi (issues) dan nilai default. Baris yang diedit lagi saat penyimpanan berjalan tidak ditimpa.
 */
export function useBatchRows(cid, bid, initialRows, onServer) {
  const [rows, setRows] = useState(initialRows)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const dirty = useRef(new Map()) // id -> { schema_id, data }
  const timer = useRef(null)
  const inflight = useRef(Promise.resolve())

  useEffect(() => { setRows(initialRows) }, [initialRows])

  const reconcile = useCallback((serverRows) => {
    setRows((local) => {
      const byId = new Map(local.map((r) => [r.id, r]))
      const out = serverRows.map((sr) => {
        const lr = byId.get(sr.id)
        if (lr && dirty.current.has(sr.id)) return { ...lr, issues: sr.issues, kbki_guess: sr.kbki_guess }
        return sr
      })
      return out
    })
  }, [])

  const send = useCallback(async (payload) => {
    setSaving(true); setError(null)
    try {
      const r = await api(`${C(cid)}/batches/${bid}/rows`, { method: 'PUT', body: payload })
      reconcile(r.rows)
      onServer?.(r.ringkasan)
      return r
    } catch (e) { setError(e); throw e } finally { setSaving(false) }
  }, [cid, bid, reconcile, onServer])

  const flush = useCallback(() => {
    clearTimeout(timer.current)
    if (!dirty.current.size) return inflight.current
    const batch = [...dirty.current.entries()].map(([id, v]) => ({ id, schema_id: v.schema_id, data: v.data }))
    const sent = new Map(dirty.current)
    dirty.current = new Map()
    inflight.current = inflight.current.then(() => send({ rows: batch })).catch(() => {
      // kembalikan ke antrean agar tidak hilang
      sent.forEach((v, id) => { if (!dirty.current.has(id)) dirty.current.set(id, v) })
    })
    return inflight.current
  }, [send])

  const schedule = useCallback(() => {
    clearTimeout(timer.current)
    timer.current = setTimeout(flush, 700)
  }, [flush])

  useEffect(() => () => clearTimeout(timer.current), [])

  const edit = useCallback((id, letter, value, schemaId) => {
    setRows((rs) => rs.map((r) => (r.id === id ? { ...r, data: { ...r.data, [letter]: value }, ...(schemaId ? { schema_id: schemaId } : {}) } : r)))
    const cur = dirty.current.get(id) || { schema_id: undefined, data: {} }
    cur.data[letter] = value
    if (schemaId) cur.schema_id = schemaId
    dirty.current.set(id, cur)
    schedule()
  }, [schedule])

  const setSchema = useCallback((id, schemaId) => {
    setRows((rs) => rs.map((r) => (r.id === id ? { ...r, schema_id: schemaId } : r)))
    const cur = dirty.current.get(id) || { schema_id: undefined, data: {} }
    cur.schema_id = schemaId
    dirty.current.set(id, cur)
    // pindah kategori dikirim segera supaya default/KBKI dihitung ulang
    clearTimeout(timer.current)
    timer.current = setTimeout(flush, 100)
  }, [flush])

  /** Tambah/ubah banyak baris sekaligus (paste, tambah baris, duplikat). */
  const bulk = useCallback(async (items) => {
    await flush()
    return send({ rows: items })
  }, [flush, send])

  const remove = useCallback(async (ids) => {
    await flush()
    setRows((rs) => rs.filter((r) => !ids.includes(r.id)))
    return send({ rows: [], delete_ids: ids })
  }, [flush, send])

  return { rows, saving, error, edit, setSchema, bulk, remove, flush, pending: () => dirty.current.size }
}
