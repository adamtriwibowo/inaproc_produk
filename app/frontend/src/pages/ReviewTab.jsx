import { useState } from 'react'
import { AlertTriangle, CheckCircle2, Download, Undo2 } from 'lucide-react'
import { api, C, download } from '../api.js'
import { Chip, ErrorBox, Spinner, useToast } from '../components/ui.jsx'

const rp = (n) => (n ? `Rp ${Number(n).toLocaleString('id-ID')}` : '—')
const WARN_TEXT = 'Produk akan langsung TAYANG dan bisa dibeli setelah diunggah. Unggahan tidak bisa dibatalkan.'

export default function ReviewTab({ cid, role, batch, rows, photos, summary, onChanged, onGoto, nErr }) {
  const toast = useToast()
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [placeholder, setPlaceholder] = useState('')
  const [result, setResult] = useState(null)
  const base = `${C(cid)}/batches/${batch.id}`

  const run = async (path, body, msg) => {
    setErr(null); setBusy(true)
    try { const r = await api(`${base}/${path}`, { method: 'POST', body }); if (msg) toast(msg); await onChanged(); return r } catch (x) { setErr(x) } finally { setBusy(false) }
  }
  const photoOf = (r) => photos.find((p) => p.row_id === r.id) || photos.find((p) => p.filename.toLowerCase() === String(r.data.E || '').toLowerCase())
  const exportNow = async () => {
    const r = await run('export', { confirm: confirmed, placeholder_url: placeholder || null }, 'Ekspor selesai')
    if (r) setResult(r)
  }

  const canReview = role === 'reviewer'
  const canExport = role === 'admin' || role === 'reviewer'
  const exportable = batch.status === 'Disetujui' || batch.status === 'Diekspor'
  const cats = Object.entries(summary.per_kategori)

  return (
    <div className="space-y-4">
      <ErrorBox error={err} />

      <section className="card p-4">
        <h2 className="mb-2 font-semibold">Ringkasan batch</h2>
        <div className="mb-3 flex flex-wrap gap-2 text-sm">
          <Chip tone="info" icon={false}>{summary.total} produk</Chip>
          <Chip tone={nErr ? 'bad' : 'ok'}>{nErr ? `${nErr} error` : 'Tanpa error'}</Chip>
          <Chip tone={summary.kbki_tebakan ? 'warn' : 'ok'}>{summary.kbki_tebakan} KBKI tebakan</Chip>
          <Chip tone={summary.foto_tanpa_link ? 'warn' : 'ok'}>{summary.foto_tanpa_link} foto belum punya link</Chip>
        </div>
        <table className="w-full">
          <thead><tr><th className="th">Kategori</th><th className="th text-right">Produk</th><th className="th text-right">Harga termurah</th><th className="th text-right">Harga termahal</th></tr></thead>
          <tbody className="divide-y divide-line">
            {cats.map(([k, v]) => <tr key={k}><td className="td">{k}</td><td className="td text-right font-mono">{v.jumlah}</td><td className="td text-right font-mono">{rp(v.harga_min)}</td><td className="td text-right font-mono">{rp(v.harga_max)}</td></tr>)}
          </tbody>
        </table>
      </section>

      {summary.peringatan.length > 0 && (
        <section className="card border-warn/40 p-4">
          <h2 className="mb-2 flex items-center gap-2 font-semibold text-warn"><AlertTriangle className="h-4 w-4" aria-hidden /> Peringatan ({summary.peringatan.length})</h2>
          <ul className="max-h-48 space-y-1 overflow-auto text-sm">
            {summary.peringatan.map((w, i) => (
              <li key={i}><button className="text-left hover:underline" onClick={() => onGoto({ row_id: w.row_id, col: w.msg.includes('KBKI') ? 'Q' : 'E' })}><b>{w.nama || '(tanpa nama)'}</b> — {w.msg}</button></li>
            ))}
          </ul>
        </section>
      )}

      <section className="card p-4">
        <h2 className="mb-2 font-semibold">Galeri produk</h2>
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6">
          {rows.map((r) => {
            const p = photoOf(r)
            return (
              <li key={r.id} className="overflow-hidden rounded-md border border-line">
                {p ? <img src={`/api${base}/photos/${p.id}/file`} alt={r.data.D || 'Produk'} loading="lazy" width="700" height="700" className="aspect-square w-full bg-muted object-contain" />
                  : <div className="flex aspect-square items-center justify-center bg-muted p-2 text-center text-xs text-muted-fg">{/^https?:/.test(r.data.E || '') ? <img src={r.data.E} alt={r.data.D || 'Produk'} loading="lazy" className="max-h-full" /> : 'Tanpa pratinjau'}</div>}
                <div className="p-2 text-xs"><div className="line-clamp-2 font-medium">{r.data.D}</div><div className="font-mono text-muted-fg">{rp(r.data.AC)}</div></div>
              </li>
            )
          })}
        </ul>
      </section>

      {batch.status === 'Diajukan' && canReview && (
        <section className="card p-4">
          <h2 className="mb-2 font-semibold">Keputusan Reviewer</h2>
          <textarea className="input mb-2" rows={2} placeholder="Catatan (wajib saat mengembalikan)" aria-label="Catatan reviewer" value={note} onChange={(e) => setNote(e.target.value)} />
          <div className="flex gap-2">
            <button className="btn btn-primary" disabled={busy} onClick={() => run('approve', {}, 'Batch disetujui')}><CheckCircle2 className="h-4 w-4" /> Setujui</button>
            <button className="btn" disabled={busy || !note.trim()} onClick={() => run('return', { note }, 'Batch dikembalikan')}><Undo2 className="h-4 w-4" /> Kembalikan untuk perbaikan</button>
          </div>
          <p className="mt-2 text-xs text-muted-fg">Reviewer tidak bisa menyetujui batch yang ia buat sendiri.</p>
        </section>
      )}
      {batch.status === 'Disetujui' && canReview && (
        <section className="card p-4">
          <textarea className="input mb-2" rows={2} placeholder="Catatan pengembalian" aria-label="Catatan pengembalian" value={note} onChange={(e) => setNote(e.target.value)} />
          <button className="btn" disabled={busy || !note.trim()} onClick={() => run('return', { note }, 'Batch dikembalikan')}><Undo2 className="h-4 w-4" /> Batalkan persetujuan</button>
        </section>
      )}

      {exportable && canExport && (
        <section className="card border-bad/40 p-4">
          <h2 className="mb-2 font-semibold">Ekspor zip untuk INAPROC</h2>
          <div role="alert" className="mb-3 flex items-start gap-2 rounded-md bg-bad-bg p-3 text-sm font-semibold text-bad">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden /> {WARN_TEXT}
          </div>
          {batch.is_test && (
            <div className="mb-3">
              <label className="label" htmlFor="ph">Link contoh foto untuk uji coba (.png) — dipakai bila foto belum punya link publik</label>
              <input id="ph" className="input font-mono text-xs" placeholder="https://i.imgur.com/xxxx.png" value={placeholder} onChange={(e) => setPlaceholder(e.target.value)} />
              <p className="mt-1 text-xs text-muted-fg">Status produk diekspor “Tidak Tayang” untuk uji coba, tetapi INAPROC mengabaikannya. Hapus produk dummy segera setelah tes.</p>
            </div>
          )}
          <label className="mb-3 flex items-start gap-2 text-sm font-medium">
            <input type="checkbox" className="mt-1" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
            Saya mengerti: produk langsung tayang dan unggahan tidak bisa dibatalkan.
          </label>
          <button className="btn btn-danger" disabled={!confirmed || busy} onClick={exportNow}>{busy ? <Spinner /> : <Download className="h-4 w-4" />} Buat zip unggahan</button>
          {result && (
            <ul className="mt-3 space-y-1 text-sm">
              {result.files.map((f) => (
                <li key={f.name}><button className="font-medium text-primary hover:underline" onClick={() => download(f.url, f.name)}><Download className="mr-1 inline h-4 w-4" />{f.name}</button> <span className="text-xs text-muted-fg">{(f.size / 1024).toFixed(0)} KB {f.name.endsWith('.xlsx') ? '(laporan — jangan masukkan ke zip unggahan)' : ''}</span></li>
              ))}
              {result.pengingat_uji && <li className="text-warn">{result.pengingat_uji}</li>}
              <li className="text-xs text-muted-fg">Langkah berikutnya: unggah zip di INAPROC (Atur Produk Sekaligus → Unggah Dokumen), lalu catat hasilnya di tab Riwayat unggah.</li>
            </ul>
          )}
        </section>
      )}
      {!exportable && <p className="text-sm text-muted-fg">Zip hanya bisa dibuat setelah batch <b>Disetujui</b> Reviewer.</p>}
    </div>
  )
}
