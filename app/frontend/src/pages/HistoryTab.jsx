import { useState } from 'react'
import { CheckCircle2, XCircle } from 'lucide-react'
import { api, C } from '../api.js'
import { Chip, Empty, ErrorBox, Loading, useLoad, useToast } from '../components/ui.jsx'

export default function HistoryTab({ cid, bid, batch, rows, onChanged }) {
  const toast = useToast()
  const base = `${C(cid)}/batches/${bid}`
  const { data, loading, error, reload } = useLoad(() => api(`${base}/history`), [cid, bid, batch.status])
  const [f, setF] = useState({ file_name: '', result: 'berhasil', message: '', reopen: true })
  const [sel, setSel] = useState([])
  const [err, setErr] = useState(null)
  const can = ['Diekspor', 'Sudah Diunggah', 'Perlu Perbaikan'].includes(batch.status)

  const submit = async (e) => {
    e.preventDefault(); setErr(null)
    try {
      await api(`${base}/history`, { method: 'POST', body: { ...f, row_ids: f.result === 'gagal' ? sel : [] } })
      toast('Hasil unggah dicatat'); setSel([]); setF({ ...f, message: '' }); reload(); onChanged()
    } catch (x) { setErr(x) }
  }
  const markDone = async () => {
    setErr(null)
    try { await api(`${base}/mark-uploaded`, { method: 'POST', body: { note: 'Semua file berhasil diunggah di INAPROC' } }); toast('Batch ditandai Sudah Diunggah'); reload(); onChanged() } catch (x) { setErr(x) }
  }

  return (
    <div className="space-y-4">
      <ErrorBox error={err || error} />
      <p className="rounded-md bg-primary/10 p-2.5 text-sm text-primary">Unggah zip dilakukan manusia di INAPROC (Atur Produk Sekaligus → Unggah Dokumen). Lihat hasilnya di tab <b>Riwayat</b> INAPROC, lalu catat di sini.</p>
      {batch.status === 'Diekspor' && <button className="btn btn-primary" onClick={markDone}><CheckCircle2 className="h-4 w-4" /> Tandai Sudah Diunggah</button>}

      {can && (
        <form onSubmit={submit} className="card space-y-3 p-4">
          <h2 className="font-semibold">Catat hasil unggah</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            <div><label className="label" htmlFor="hf">Nama file (opsional)</label><input id="hf" className="input" value={f.file_name} onChange={(e) => setF({ ...f, file_name: e.target.value })} /></div>
            <div><label className="label" htmlFor="hr">Hasil</label><select id="hr" className="input" value={f.result} onChange={(e) => setF({ ...f, result: e.target.value })}><option value="berhasil">Berhasil</option><option value="gagal">Gagal</option></select></div>
            <div><label className="label" htmlFor="hm">Pesan dari INAPROC</label><input id="hm" className="input" value={f.message} onChange={(e) => setF({ ...f, message: e.target.value })} /></div>
          </div>
          {f.result === 'gagal' && (
            <>
              <fieldset className="max-h-40 overflow-auto rounded-md border border-line p-2">
                <legend className="px-1 text-xs text-muted-fg">Baris yang gagal</legend>
                {rows.map((r, i) => (
                  <label key={r.id} className="flex items-center gap-2 py-0.5 text-sm"><input type="checkbox" checked={sel.includes(r.id)} onChange={(e) => setSel(e.target.checked ? [...sel, r.id] : sel.filter((x) => x !== r.id))} /> {i + 1}. {r.data.D}</label>
                ))}
              </fieldset>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.reopen} onChange={(e) => setF({ ...f, reopen: e.target.checked })} /> Buka kembali batch untuk diperbaiki (status Perlu Perbaikan)</label>
            </>
          )}
          <button className="btn btn-primary">Simpan catatan</button>
        </form>
      )}

      <div className="card overflow-x-auto">
        {loading ? <Loading /> : (
          <table className="w-full">
            <thead><tr><th className="th">Waktu</th><th className="th">File</th><th className="th">Hasil</th><th className="th">Pesan</th></tr></thead>
            <tbody className="divide-y divide-line">
              {data.map((h) => (
                <tr key={h.id}>
                  <td className="td whitespace-nowrap font-mono text-xs">{new Date(h.ts).toLocaleString('id-ID')}</td>
                  <td className="td text-xs">{h.file_name || '—'}</td>
                  <td className="td"><Chip tone={h.result === 'berhasil' ? 'ok' : 'bad'}>{h.result === 'berhasil' ? 'Berhasil' : 'Gagal'}</Chip></td>
                  <td className="td text-xs">{h.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {!loading && data.length === 0 && <Empty>Belum ada riwayat.</Empty>}
      </div>
      {rows.some((r) => r.upload_status === 'gagal') && (
        <div className="card border-bad/40 p-3 text-sm">
          <h3 className="mb-1 flex items-center gap-1 font-semibold text-bad"><XCircle className="h-4 w-4" /> Baris yang gagal diunggah</h3>
          <ul className="list-disc pl-5">{rows.filter((r) => r.upload_status === 'gagal').map((r) => <li key={r.id}>{r.data.D} — {r.upload_message}</li>)}</ul>
        </div>
      )}
    </div>
  )
}
