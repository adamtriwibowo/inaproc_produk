import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AlertTriangle, ArrowLeft, Download, FileUp, FlaskConical, Plus, Send } from 'lucide-react'
import { api, C, download } from '../api.js'
import { useCompany } from '../company.js'
import { Chip, ErrorBox, Loading, Spinner, statusTone, useLoad, useToast } from '../components/ui.jsx'
import Grid, { buildColumns, optionsFor } from '../components/Grid.jsx'
import { useBatchRows } from '../useBatchRows.js'
import PhotosTab from './PhotosTab.jsx'
import ReviewTab from './ReviewTab.jsx'
import HistoryTab from './HistoryTab.jsx'

const EDITABLE = ['Draft', 'Perlu Perbaikan']
const TABS = [['grid', 'Input produk'], ['foto', 'Foto'], ['review', 'Review & Ekspor'], ['riwayat', 'Riwayat unggah']]

export default function BatchEditor() {
  const { cid, role } = useCompany()
  const { bid } = useParams()
  const full = useLoad(async () => {
    const [b, t] = await Promise.all([api(`${C(cid)}/batches/${bid}`), api(`${C(cid)}/templates?full=true`)])
    return { b, t }
  }, [cid, bid])
  if (full.loading) return <Loading />
  if (full.error) return <ErrorBox error={full.error} />
  return <Editor cid={cid} role={role} init={full.data.b} schemas={full.data.t} reloadAll={full.reload} />
}

function Editor({ cid, role, init, schemas, reloadAll }) {
  const toast = useToast()
  const [batch, setBatch] = useState(init.batch)
  const [summary, setSummary] = useState(init.ringkasan)
  const [photos, setPhotos] = useState(init.photos)
  const [tab, setTab] = useState('grid')
  const [jenis, setJenis] = useState('Barang')
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)
  const [showErrors, setShowErrors] = useState(true)
  const importRef = useRef(null)
  const bid = batch.id

  const store = useBatchRows(cid, bid, init.rows, setSummary)
  const { rows } = store
  const editable = EDITABLE.includes(batch.status) && (role === 'admin' || role === 'operator')
  const schemaOf = useMemo(() => Object.fromEntries(schemas.map((s) => [s.id, s])), [schemas])
  const jenisOf = (r) => schemaOf[r.schema_id]?.jenis
  const gridRows = useMemo(() => rows.filter((r) => (jenisOf(r) || 'Barang') === jenis), [rows, jenis, schemaOf])
  const cols = useMemo(() => buildColumns(schemas, jenis), [schemas, jenis])
  const schemasOfJenis = useMemo(() => schemas.filter((s) => s.jenis === jenis), [schemas, jenis])
  const counts = useMemo(() => ({
    Barang: rows.filter((r) => (jenisOf(r) || 'Barang') === 'Barang').length,
    Jasa: rows.filter((r) => jenisOf(r) === 'Jasa').length,
  }), [rows, schemaOf])

  const refreshBatch = useCallback(async () => {
    const d = await api(`${C(cid)}/batches/${bid}`)
    setBatch(d.batch); setSummary(d.ringkasan); setPhotos(d.photos)
    return d
  }, [cid, bid])

  // ---------- handler grid (identitas stabil lewat ref) ----------
  const live = useRef({})
  live.current = { rows: gridRows, cols, schemaOf, schemasOfJenis, store, jenis }
  const handlers = useMemo(() => {
    const L = () => live.current
    const focusCell = (rowId, letter) => {
      const el = document.getElementById(`cell-${rowId}-${letter}`)
      if (el) { el.focus(); el.scrollIntoView({ block: 'nearest', inline: 'nearest' }); el.select?.() }
    }
    const newItem = (schemaId, data = {}) => ({ schema_id: schemaId, data })
    const apply = async (items) => {
      try { await L().store.bulk(items) } catch (e) { setErr(e) }
    }
    return {
      focusCell,
      edit: (id, letter, v) => L().store.edit(id, letter, v),
      setSchema: (id, sid) => L().store.setSchema(id, sid),
      remove: async (row) => { if (confirm('Hapus baris ini?')) try { await L().store.remove([row.id]) } catch (e) { setErr(e) } },
      duplicate: (row) => apply([newItem(row.schema_id, { ...row.data })]),
      keyDown: (e, rowId, letter) => {
        const list = L().rows
        const i = list.findIndex((r) => r.id === rowId)
        const isSelect = e.target.tagName === 'SELECT'
        if (e.key === 'Enter' || (!isSelect && (e.key === 'ArrowDown' || e.key === 'ArrowUp'))) {
          const n = list[i + (e.key === 'ArrowUp' ? -1 : 1)]
          if (n) { e.preventDefault(); focusCell(n.id, letter) }
        }
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'd' && letter !== '_kat') { // isi ke bawah dari sel di atas
          e.preventDefault()
          const prev = list[i - 1]
          if (prev) L().store.edit(rowId, letter, prev.data[letter] ?? '')
        }
      },
      fillColumn: (col) => {
        const list = L().rows
        if (list.length < 2) return
        const v = list[0].data[col.letter] ?? ''
        if (!confirm(`Isi kolom “${col.label}” pada ${list.length - 1} baris di bawah dengan nilai baris pertama?`)) return
        apply(list.slice(1).filter((r) => col.schemaIds.has(r.schema_id)).map((r) => ({ id: r.id, schema_id: r.schema_id, data: { [col.letter]: v } })))
      },
      paste: (e, rowId, letter) => {
        const text = e.clipboardData.getData('text')
        const trimmed = text.replace(/\r/g, '').replace(/\n$/, '')
        if (!/[\t\n]/.test(trimmed)) return // tempel nilai tunggal = perilaku normal
        e.preventDefault()
        const { rows: list, cols: cs, schemaOf: so, schemasOfJenis: sj } = L()
        const gridCols = [{ letter: '_kat' }, ...cs]
        const r0 = list.findIndex((r) => r.id === rowId)
        const c0 = gridCols.findIndex((c) => c.letter === letter)
        const matrix = trimmed.split('\n').map((l) => l.split('\t'))
        const baseSchema = list[r0]?.schema_id || sj[0]?.id
        const items = matrix.map((line, i) => {
          const target = list[r0 + i]
          let sid = target?.schema_id || baseSchema
          line.forEach((val, j) => {
            if (gridCols[c0 + j]?.letter === '_kat') {
              const s = sj.find((x) => x.category_name.toLowerCase() === val.trim().toLowerCase())
              if (s) sid = s.id
            }
          })
          const data = {}
          line.forEach((val, j) => {
            const col = gridCols[c0 + j]
            if (!col || col.letter === '_kat' || !col.schemaIds?.has(sid)) return
            let v = val.trim()
            const opts = optionsFor(so[sid], col)
            const hit = opts?.find((o) => o[0].toLowerCase() === v.toLowerCase() || o[1].toLowerCase() === v.toLowerCase())
            if (hit) v = hit[0]
            data[col.letter] = v
          })
          return { id: target?.id, schema_id: sid, data }
        })
        apply(items)
        toast(`${items.length} baris ditempel`)
      },
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const addRows = async (n = 1) => {
    const sid = schemasOfJenis[0]?.id
    if (!sid) { setErr({ message: `Belum ada template ${jenis}. Unggah template di menu Template.` }); return }
    setErr(null)
    try { await store.bulk(Array.from({ length: n }, () => ({ schema_id: sid, data: {} }))) } catch (e) { setErr(e) }
  }

  const importForm = async (e) => {
    const f = e.target.files[0]; if (!f) return
    setErr(null); setBusy(true)
    const form = new FormData(); form.append('file', f)
    try {
      const r = await api(`${C(cid)}/batches/${bid}/import-form`, { method: 'POST', form })
      toast(`${r.diimpor} baris diimpor${r.dilewati.length ? `, ${r.dilewati.length} dilewati` : ''}`, r.diimpor ? 'ok' : 'bad')
      if (r.dilewati.length) setErr({ message: 'Sebagian baris dilewati', detail: { detail: r.dilewati } })
      reloadAll()
    } catch (x) { setErr(x) } finally { setBusy(false); e.target.value = '' }
  }

  const action = async (path, body, okMsg) => {
    setErr(null); setBusy(true)
    try {
      await store.flush()
      await api(`${C(cid)}/batches/${bid}/${path}`, { method: 'POST', body: body || {} })
      toast(okMsg)
      await refreshBatch()
    } catch (x) { setErr(x) } finally { setBusy(false) }
  }

  const goTo = (item) => {
    setTab('grid')
    const row = rows.find((r) => r.id === item.row_id)
    if (row) setJenis(jenisOf(row) || 'Barang')
    setTimeout(() => handlers.focusCell(item.row_id, item.col), 60)
  }

  // daftar error untuk panel (klik -> sel)
  const errorItems = useMemo(() => {
    const out = []
    rows.forEach((r, idx) => {
      const sc = schemaOf[r.schema_id]
      for (const i of r.issues || []) {
        const col = i.col === 'kategori' ? null : sc?.columns.find((c) => c.letter === i.col)
        out.push({ row_id: r.id, no: idx + 1, nama: r.data.D || '(tanpa nama)', col: i.col === 'kategori' ? '_kat' : i.col, label: SHORT_LABEL(col, i.col), msg: i.msg, level: i.level })
      }
    })
    return out
  }, [rows, schemaOf])
  const nErr = errorItems.filter((x) => x.level === 'error').length

  const canSubmit = (role === 'admin' || role === 'operator') && EDITABLE.includes(batch.status)

  return (
    <>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <Link to={`/c/${cid}/batch`} className="btn btn-sm"><ArrowLeft className="h-4 w-4" /> Batch</Link>
        <h1 className="text-2xl font-bold tracking-tight">{batch.name}</h1>
        <Chip tone={statusTone(batch.status)}>{batch.status}</Chip>
        {batch.is_test && <Chip tone="warn"><FlaskConical className="h-3 w-3" /> Uji coba</Chip>}
        <span className="text-xs text-muted-fg">Preset PDN: {batch.pdn_preset}</span>
        <span className="ml-auto flex items-center gap-2 text-xs text-muted-fg" role="status" aria-live="polite">
          {store.saving ? <><Spinner /> Menyimpan…</> : 'Tersimpan otomatis'}
        </span>
        {canSubmit && (
          <button className="btn btn-primary" disabled={busy || nErr > 0 || rows.length === 0} onClick={() => action('submit', null, 'Batch diajukan ke Reviewer')}
            title={nErr > 0 ? 'Perbaiki semua error dulu' : ''}>
            <Send className="h-4 w-4" /> Ajukan ke Review
          </button>
        )}
      </div>
      {batch.is_test && (
        <div className="mb-3 flex items-start gap-2 rounded-md bg-warn-bg p-2.5 text-sm text-warn" role="note">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          Batch uji coba: <b>hapus produk dummy dari INAPROC segera setelah tes</b>. Status “Tidak Tayang” di template diabaikan INAPROC — produk tetap tayang.
        </div>
      )}
      {batch.review_note && batch.status === 'Perlu Perbaikan' && (
        <div role="alert" className="mb-3 rounded-md border border-warn/40 bg-warn-bg p-2.5 text-sm text-warn"><b>Catatan Reviewer:</b> {batch.review_note}</div>
      )}
      <ErrorBox error={err || store.error} />

      <div className="mb-4 flex gap-1 border-b border-line" role="tablist">
        {TABS.map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`border-b-2 px-4 py-2.5 text-sm font-semibold transition-colors duration-200 ${tab === k ? 'border-primary text-primary' : 'border-transparent text-muted-fg hover:text-fg'}`}>
            {l}{k === 'grid' && nErr > 0 && <span className="chip ml-1.5 bg-bad-bg text-bad">{nErr}</span>}
          </button>
        ))}
      </div>

      {tab === 'grid' && (
        <>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <div className="flex gap-1" role="group" aria-label="Jenis produk">
              {['Barang', 'Jasa'].map((j) => (
                <button key={j} className={`btn btn-sm ${jenis === j ? 'btn-primary' : ''}`} aria-pressed={jenis === j} onClick={() => setJenis(j)}>{j} ({counts[j]})</button>
              ))}
            </div>
            {editable && (
              <>
                <button className="btn btn-sm" onClick={() => addRows(1)}><Plus className="h-4 w-4" /> Baris</button>
                <button className="btn btn-sm" onClick={() => addRows(10)}><Plus className="h-4 w-4" /> 10 baris</button>
                <input ref={importRef} type="file" accept=".xlsx" hidden onChange={importForm} />
                <button className="btn btn-sm" disabled={busy} onClick={() => importRef.current.click()}><FileUp className="h-4 w-4" /> Impor Form_Data_Produk.xlsx</button>
                <label className="flex items-center gap-1 text-xs text-muted-fg">Preset PDN
                  <select className="input !min-h-[30px] w-24 !py-0 text-xs" value={batch.pdn_preset} onChange={async (e) => { setBatch(await api(`${C(cid)}/batches/${bid}`, { method: 'PATCH', body: { pdn_preset: e.target.value } })) }}>
                    <option>Lokal</option><option>Impor</option>
                  </select>
                </label>
              </>
            )}
            <button className="btn btn-sm" onClick={() => download(`${C(cid)}/templates/blank-form`, 'Form_Data_Produk_kosong.xlsx')}><Download className="h-4 w-4" /> Form kosong</button>
            <button className="btn btn-sm ml-auto" onClick={() => setShowErrors((s) => !s)} aria-expanded={showErrors}>
              {nErr > 0 ? <><AlertTriangle className="h-4 w-4 text-bad" /> {nErr} error</> : 'Tidak ada error'} · {summary.warn} peringatan
            </button>
          </div>
          <details className="mb-3 text-sm text-muted-fg">
            <summary className="w-fit cursor-pointer font-semibold text-primary">Tips mengisi grid</summary>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              <li>Tempel dari Excel di sel mana pun (Ctrl+V). Baris baru dibuat otomatis.</li>
              <li><kbd className="rounded border border-line bg-card px-1">Ctrl+D</kbd> menyalin dari sel di atas. Tombol panah di judul kolom mengisi seluruh kolom.</li>
              <li>Harga dan stok berupa bilangan bulat tanpa pemisah (85000, bukan 85.000).</li>
              <li>Tidak tersedia di unggah massal: varian, harga grosir, layanan tambahan, merek, TKDN, SNI. Isi manual di INAPROC setelah produk masuk.</li>
            </ul>
          </details>
          <div className={`grid gap-3 ${showErrors && errorItems.length ? 'xl:grid-cols-[1fr_320px]' : ''}`}>
            <div className="min-w-0">
              {schemasOfJenis.length === 0 ? (
                <div className="card p-6 text-center text-sm text-muted-fg">Belum ada template {jenis} untuk perusahaan ini.</div>
              ) : gridRows.length === 0 ? (
                <div className="card p-8 text-center text-sm text-muted-fg">
                  Belum ada produk {jenis}. {editable ? 'Klik “+ Baris”, tempel dari Excel, atau impor Form_Data_Produk.xlsx.' : ''}
                </div>
              ) : (
                <Grid rows={gridRows} cols={cols} schemas={schemas} schemasOfJenis={schemasOfJenis} readOnly={!editable} handlers={handlers} />
              )}
            </div>
            {showErrors && errorItems.length > 0 && (
              <aside className="card max-h-[calc(100vh-280px)] overflow-auto" aria-label="Panel error validasi">
                <h2 className="sticky top-0 border-b border-line bg-card px-3 py-2 text-sm font-semibold">Error & peringatan ({errorItems.length})</h2>
                <ul className="divide-y divide-line">
                  {errorItems.map((x, i) => (
                    <li key={i}>
                      <button className="block w-full px-3 py-2 text-left text-xs hover:bg-muted" onClick={() => goTo(x)}>
                        <span className={`font-semibold ${x.level === 'error' ? 'text-bad' : 'text-warn'}`}>{x.level === 'error' ? '✕' : '⚠'} Baris {x.no} · {x.label}</span>
                        <span className="block truncate text-muted-fg">{x.nama}</span>
                        <span className="block">{x.msg}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </aside>
            )}
          </div>
        </>
      )}

      {tab === 'foto' && (
        <PhotosTab cid={cid} bid={bid} batch={batch} rows={rows} photos={photos} editable={editable} onChanged={async () => { await refreshBatch(); reloadAll() }} schemaOf={schemaOf} />
      )}
      {tab === 'review' && (
        <ReviewTab cid={cid} role={role} batch={batch} rows={rows} photos={photos} summary={summary} schemaOf={schemaOf} onChanged={refreshBatch} onGoto={goTo} nErr={nErr} />
      )}
      {tab === 'riwayat' && <HistoryTab cid={cid} bid={bid} batch={batch} rows={rows} role={role} onChanged={refreshBatch} />}
    </>
  )
}

function SHORT_LABEL(col, letter) {
  if (letter === '_kat' || letter === 'kategori') return 'Kategori'
  return col?.label?.length > 40 ? `${col.label.slice(0, 38)}…` : col?.label || letter
}
