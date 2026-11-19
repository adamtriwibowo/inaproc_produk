import { useRef, useState } from 'react'
import { Download, Trash2, Upload } from 'lucide-react'
import { api, C, download } from '../api.js'
import { useCompany } from '../company.js'
import { Chip, ErrorBox, Loading, PageHeader, useLoad, useToast } from '../components/ui.jsx'

export default function Templates() {
  const { cid, role } = useCompany()
  const toast = useToast()
  const { data, error, loading, reload } = useLoad(() => api(`${C(cid)}/templates`), [cid])
  const [err, setErr] = useState(null)
  const [rejected, setRejected] = useState([])
  const [busy, setBusy] = useState(false)
  const ref = useRef(null)
  const admin = role === 'admin'

  const upload = async (e) => {
    const files = [...e.target.files]; if (!files.length) return
    setErr(null); setBusy(true)
    const form = new FormData(); files.forEach((f) => form.append('files', f))
    try {
      const r = await api(`${C(cid)}/templates`, { method: 'POST', form })
      setRejected(r.ditolak)
      toast(`${r.diterima.length} template diterima${r.ditolak.length ? `, ${r.ditolak.length} ditolak` : ''}`, r.ditolak.length && !r.diterima.length ? 'bad' : 'ok')
      reload()
    } catch (x) { setErr(x) } finally { setBusy(false); e.target.value = '' }
  }
  const del = async (t) => {
    if (!confirm(`Hapus template ${t.category_name}?`)) return
    try { await api(`${C(cid)}/templates/${t.id}`, { method: 'DELETE' }); reload() } catch (x) { setErr(x) }
  }

  if (loading) return <Loading />
  if (error) return <ErrorBox error={error} />
  return (
    <>
      <PageHeader
        title="Template INAPROC"
        subtitle="Skema kolom dibaca otomatis dari template resmi INAPROC. Institution ID template harus sama dengan perusahaan aktif."
        actions={(
          <>
            <button className="btn" onClick={() => download(`${C(cid)}/templates/blank-form`, 'Form_Data_Produk_kosong.xlsx')}><Download className="h-4 w-4" /> Form kosong</button>
            {admin && (
              <>
                <input ref={ref} type="file" multiple accept=".xlsx,.zip" hidden onChange={upload} />
                <button className="btn btn-primary" disabled={busy} onClick={() => ref.current.click()}><Upload className="h-4 w-4" /> Unggah template (.xlsx / .zip)</button>
              </>
            )}
          </>
        )}
      />
      <ErrorBox error={err} />
      {rejected.length > 0 && (
        <div role="alert" className="mb-3 rounded-md border border-bad/30 bg-bad-bg p-3 text-sm text-bad">
          <b>Template ditolak:</b>
          <ul className="mt-1 list-disc pl-5">{rejected.map((r) => <li key={r.file}><span className="font-mono text-xs">{r.file}</span> — {r.alasan}</li>)}</ul>
        </div>
      )}
      <p className="mb-3 text-sm text-muted-fg">
        Kategori belum punya template? Unduh di INAPROC: Produk › Atur Produk Sekaligus › Unduh Template (maksimal 100 kategori per unduhan, dikirim lewat email), lalu unggah di sini.
      </p>
      <div className="card overflow-x-auto">
        <table className="tbl">
          <thead><tr><th className="th">Kategori</th><th className="th">Jenis</th><th className="th">Kategori di pohon</th><th className="th text-right">Kolom</th><th className="th text-right">KBKI</th>{admin && <th className="th"><span className="sr-only">Aksi</span></th>}</tr></thead>
          <tbody className="divide-y divide-line">
            {data.map((t) => (
              <tr key={t.id}>
                <td className="td font-medium">{t.category_name}<div className="font-mono text-[11px] text-muted-fg">{t.category_uuid}</div></td>
                <td className="td"><Chip tone={t.jenis === 'Jasa' ? 'info' : 'mute'} icon={false}>{t.jenis}</Chip></td>
                <td className="td text-xs">{t.category_path || <span className="text-warn">belum dicocokkan</span>}</td>
                <td className="td text-right num">{t.n_kolom}</td>
                <td className="td text-right num">{t.kbki.length}</td>
                {admin && <td className="td"><button className="btn btn-sm" aria-label={`Hapus template ${t.category_name}`} onClick={() => del(t)}><Trash2 className="h-3.5 w-3.5" /></button></td>}
              </tr>
            ))}
          </tbody>
        </table>
        {data.length === 0 && <p className="p-6 text-center text-sm text-muted-fg">Belum ada template. {admin ? 'Unggah template dari INAPROC.' : 'Minta Admin Perusahaan mengunggahnya.'}</p>}
      </div>
    </>
  )
}
