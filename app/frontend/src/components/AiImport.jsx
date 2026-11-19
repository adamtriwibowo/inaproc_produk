import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, CheckCircle2, FileUp, Sparkles, UploadCloud } from 'lucide-react'
import { api, C } from '../api.js'
import { Chip, ErrorBox, Modal, Spinner, useToast } from './ui.jsx'

const usd = (n) => (n == null ? 'tidak diketahui' : `US$ ${Number(n).toFixed(n < 1 ? 3 : 2)}`)

/** Impor dokumen supplier -> Draf AI. Tahap: pilih file -> estimasi biaya -> proses (progres) -> hasil. */
export function AiImportModal({ cid, bid, onClose, onDone }) {
  const toast = useToast()
  const [phase, setPhase] = useState('pilih')
  const [files, setFiles] = useState([])
  const [ocr, setOcr] = useState(false)
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)
  const [up, setUp] = useState(null)
  const [job, setJob] = useState(null)
  const [hemat, setHemat] = useState(false)
  const input = useRef(null)
  const base = `${C(cid)}/ai`

  const upload = async () => {
    setErr(null); setBusy(true)
    const form = new FormData()
    form.append('batch_id', String(bid)); form.append('ocr', ocr ? 'true' : 'false')
    files.forEach((f) => form.append('files', f))
    try { const r = await api(`${base}/sources`, { method: 'POST', form }); setUp(r); setPhase('estimasi') } catch (x) { setErr(x) } finally { setBusy(false) }
  }
  const start = async () => {
    setErr(null); setBusy(true)
    try {
      const j = await api(`${base}/import`, { method: 'POST', body: { batch_id: bid, source_ids: up.docs.map((d) => d.id), ocr, hemat } })
      setJob(j); setPhase('proses')
    } catch (x) { setErr(x) } finally { setBusy(false) }
  }

  useEffect(() => {
    if (phase !== 'proses' || !job) return undefined
    if (['selesai', 'gagal'].includes(job.status)) { setPhase('hasil'); return undefined }
    const t = setInterval(async () => {
      try { const j = await api(`${base}/jobs/${job.id}`); setJob(j); if (['selesai', 'gagal'].includes(j.status)) setPhase('hasil') } catch (x) { setErr(x) }
    }, 1500)
    return () => clearInterval(t)
  }, [phase, job, base])

  const est = up?.estimasi
  return (
    <Modal title="Impor dari dokumen supplier (AI)" onClose={phase === 'proses' ? () => {} : onClose} wide>
      <ErrorBox error={err} />
      {phase === 'pilih' && (
        <div className="space-y-4">
          <p className="text-sm text-muted-fg">Unggah price list Excel/CSV, PDF katalog, atau foto label. AI hanya mengisi nilai yang <b>tertulis di dokumen</b>; sisanya dikosongkan. Semua hasil berstatus <b>Draf AI</b> dan harus Anda konfirmasi.</p>
          <div className="rounded-lg border-2 border-dashed border-line p-6 text-center" onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); setFiles([...files, ...e.dataTransfer.files]) }}>
            <UploadCloud className="mx-auto h-8 w-8 text-muted-fg" aria-hidden />
            <p className="mt-2 text-sm">Seret file ke sini atau <button className="font-semibold text-primary underline" onClick={() => input.current.click()}>pilih file</button></p>
            <p className="text-xs text-muted-fg">.xlsx, .csv, .pdf, .png, .jpg · maks. 10 file, 25 MB per file</p>
            <input ref={input} type="file" multiple hidden accept=".xlsx,.xlsm,.csv,.pdf,.png,.jpg,.jpeg,.webp" onChange={(e) => { setFiles([...files, ...e.target.files]); e.target.value = '' }} />
          </div>
          {files.length > 0 && (
            <ul className="space-y-1 text-sm">{files.map((f, i) => <li key={i} className="flex items-center justify-between rounded-md bg-muted/60 px-3 py-1.5"><span className="truncate">{f.name}</span><button className="text-xs font-semibold text-bad" onClick={() => setFiles(files.filter((_, j) => j !== i))}>Hapus</button></li>)}</ul>
          )}
          <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={ocr} onChange={(e) => setOcr(e.target.checked)} /> PDF ini hasil scan (pakai OCR, lebih mahal)</label>
          <div className="flex justify-end gap-2"><button className="btn" onClick={onClose}>Batal</button>
            <button className="btn btn-primary" disabled={!files.length || busy} onClick={upload}>{busy ? <Spinner /> : <FileUp className="h-4 w-4" />} Lanjut: lihat estimasi biaya</button></div>
        </div>
      )}

      {phase === 'estimasi' && up && (
        <div className="space-y-4">
          {up.ditolak.length > 0 && <div className="rounded-md bg-bad-bg p-3 text-sm text-bad"><b>Ditolak:</b> {up.ditolak.map((d) => `${d.file} (${d.alasan})`).join('; ')}</div>}
          <div className="rounded-lg border border-line p-4">
            <h3 className="mb-2 font-bold">Estimasi sebelum dijalankan</h3>
            {est ? (
              <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-4">
                <div><dt className="text-muted-fg">Perkiraan item</dt><dd className="num font-semibold">{est.item_kira2}</dd></div>
                <div><dt className="text-muted-fg">Panggilan AI</dt><dd className="num font-semibold">{est.panggilan}</dd></div>
                <div><dt className="text-muted-fg">Token</dt><dd className="num font-semibold">{(est.token_masuk + est.token_keluar).toLocaleString('id-ID')}</dd></div>
                <div><dt className="text-muted-fg">Biaya perkiraan</dt><dd className="num font-semibold">{usd(est.biaya_usd)}</dd></div>
              </dl>
            ) : <p className="text-sm text-muted-fg">Tidak ada dokumen yang valid.</p>}
            {est?.catatan?.map((c) => <p key={c} className="mt-2 text-xs text-muted-fg">{c}</p>)}
            {est && <p className="mt-2 text-xs text-muted-fg">Perkiraan kasar dari ukuran dokumen dan harga model saat ini. Biaya sebenarnya tercatat di Pengaturan AI.</p>}
            {est?.melebihi_kuota && <p className="mt-2 flex items-center gap-1.5 text-sm font-semibold text-bad"><AlertTriangle className="h-4 w-4" aria-hidden /> Perkiraan biaya melebihi sisa kuota bulan ini.</p>}
          </div>
          <label className="flex items-start gap-2 text-sm text-muted-fg"><input type="checkbox" className="mt-1" checked={hemat} onChange={(e) => setHemat(e.target.checked)} /> Mode hemat (tidak mendesak). Dicatat; dipakai bila model mendukung varian batch.</label>
          <div className="flex justify-end gap-2"><button className="btn" onClick={() => setPhase('pilih')}>Kembali</button>
            <button className="btn btn-primary" disabled={!est || busy} onClick={start}>{busy ? <Spinner /> : <Sparkles className="h-4 w-4" />} Jalankan agen AI</button></div>
        </div>
      )}

      {phase === 'proses' && job && (
        <div className="space-y-3 py-6 text-center" role="status">
          <Spinner className="mx-auto h-8 w-8" />
          <p className="font-semibold">Agen AI sedang bekerja…</p>
          <div className="mx-auto h-2.5 w-full max-w-sm overflow-hidden rounded-full bg-muted"><div className="h-full bg-primary transition-[width] duration-500" style={{ width: `${job.progress}%` }} /></div>
          <p className="text-sm text-muted-fg">{job.progress}% · jangan tutup halaman ini</p>
        </div>
      )}

      {phase === 'hasil' && job && (
        <div className="space-y-4">
          {job.status === 'gagal' ? (
            <div role="alert" className="rounded-md border border-bad/30 bg-bad-bg p-3 text-sm text-bad"><b>Gagal:</b> {job.message}</div>
          ) : (
            <>
              <div className="flex items-center gap-2 text-base font-bold text-ok"><CheckCircle2 className="h-5 w-5" aria-hidden /> {job.result.dibuat} baris Draf AI dibuat</div>
              <div className="flex flex-wrap gap-2 text-sm">
                <Chip tone="info" icon={false}>{job.result.diekstrak} item terbaca</Chip>
                {job.result.harga_kosong > 0 && <Chip tone="warn">{job.result.harga_kosong} baris harga kosong (perlu diisi)</Chip>}
                {job.result.ditandai.length > 0 && <Chip tone="warn">{job.result.ditandai.length} item tidak dibuat</Chip>}
              </div>
              <p className="text-sm text-muted-fg">Kolom yang tidak ada di dokumen dibiarkan kosong. Periksa, lengkapi, lalu klik <b>Konfirmasi Draf AI</b>.</p>
              {job.result.ditandai.length > 0 && (
                <div className="max-h-64 overflow-auto rounded-lg border border-warn/40">
                  <table className="tbl"><thead><tr><th className="th">Item</th><th className="th">Alasan</th></tr></thead>
                    <tbody>{job.result.ditandai.map((m, i) => (
                      <tr key={i}><td className="td"><div className="font-medium">{m.nama}</div><div className="text-xs text-muted-fg">{m.sumber} · {m.lokasi}</div></td>
                        <td className="td text-sm">
                          <Chip tone={m.status === 'Tidak Bisa' ? 'bad' : 'warn'}>{m.status}</Chip>
                          {m.kategori && <div className="mt-1 text-xs">Kategori terdekat: {m.kategori}</div>}
                          <div className="mt-1 text-xs text-muted-fg">{m.catatan}</div>
                          {m.kbli_dibutuhkan?.length > 0 && <div className="mt-1 text-xs">KBLI yang dibutuhkan: {m.kbli_dibutuhkan.map((k) => `${k.kode} (${k.versi})`).join(', ')}</div>}
                        </td></tr>
                    ))}</tbody></table>
                </div>
              )}
            </>
          )}
          <div className="flex justify-end"><button className="btn btn-primary" onClick={onDone}>Lihat di grid</button></div>
        </div>
      )}
    </Modal>
  )
}

/** Tinjau & konfirmasi baris Draf AI. Kolom kritis wajib dicentang eksplisit per baris. */
export function AiConfirmModal({ cid, bid, rows, critical, schemaOf, onClose, onDone }) {
  const toast = useToast()
  const draf = rows.filter((r) => r.origin === 'Draf AI' && !r.confirmed)
  const reqOf = (r) => Object.keys(critical).filter((k) => k === 'kategori' || (r.data[k] ?? '') !== '')
  const [ack, setAck] = useState({})
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)
  const toggle = (id, v) => setAck({ ...ack, [id]: v })
  const picked = draf.filter((r) => ack[r.id])
  const submit = async () => {
    setErr(null); setBusy(true)
    try {
      const r = await api(`${C(cid)}/ai/batches/${bid}/confirm`, { method: 'POST', body: { items: picked.map((x) => ({ row_id: x.id, ack: reqOf(x) })) } })
      toast(`${r.dikonfirmasi.length} baris dikonfirmasi`); onDone()
    } catch (x) { setErr(x) } finally { setBusy(false) }
  }
  return (
    <Modal title="Konfirmasi Draf AI" onClose={onClose} wide>
      <ErrorBox error={err} />
      <p className="mb-3 text-sm text-muted-fg">Periksa nilai kritis tiap baris. Centang bila sudah sesuai dengan barang dan dokumen sumber. Nilai yang Anda ubah di grid ikut terpakai.</p>
      <div className="mb-3 flex items-center gap-2">
        <button className="btn btn-sm" onClick={() => setAck(Object.fromEntries(draf.map((r) => [r.id, true])))}>Pilih semua</button>
        <button className="btn btn-sm" onClick={() => setAck({})}>Kosongkan</button>
        <span className="text-sm text-muted-fg">{picked.length} dari {draf.length} dipilih</span>
      </div>
      <ul className="max-h-[50vh] space-y-3 overflow-auto">
        {draf.map((r) => (
          <li key={r.id} className="rounded-lg border border-line p-3">
            <label className="flex items-start gap-2.5">
              <input type="checkbox" className="mt-1" checked={!!ack[r.id]} onChange={(e) => toggle(r.id, e.target.checked)} />
              <span className="min-w-0 flex-1">
                <span className="block font-semibold">{r.data.D}</span>
                <span className="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs sm:grid-cols-3">
                  <span><span className="text-muted-fg">Kategori:</span> {schemaOf[r.schema_id]?.category_name}</span>
                  {reqOf(r).filter((k) => k !== 'kategori').map((k) => <span key={k}><span className="text-muted-fg">{critical[k]}:</span> <b>{String(r.data[k]).slice(0, 40)}</b></span>)}
                </span>
                {r.ai_meta?.skor != null && <span className="mt-1 block text-xs text-muted-fg">Keyakinan kategori {Math.round(r.ai_meta.skor * 100)}%{r.ai_meta.alternatif?.length ? ` · alternatif: ${r.ai_meta.alternatif.join(', ')}` : ''}</span>}
                {r.issues.some((i) => i.level === 'error') && <span className="mt-1 block text-xs text-bad">Masih ada error validasi di baris ini.</span>}
              </span>
            </label>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex justify-end gap-2"><button className="btn" onClick={onClose}>Batal</button>
        <button className="btn btn-primary" disabled={!picked.length || busy} onClick={submit}>{busy && <Spinner />} Konfirmasi {picked.length} baris</button></div>
    </Modal>
  )
}
