import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Boxes, FlaskConical, Plus } from 'lucide-react'
import { api, C } from '../api.js'
import { useCompany } from '../company.js'
import { Chip, Empty, ErrorBox, Loading, Modal, PageHeader, statusTone, useLoad } from '../components/ui.jsx'

const FILTERS = ['Semua', 'Draft', 'Diajukan', 'Perlu Perbaikan', 'Disetujui', 'Diekspor', 'Sudah Diunggah']

export default function Batches() {
  const { cid, role } = useCompany()
  const nav = useNavigate()
  const { data, error, loading } = useLoad(() => api(`${C(cid)}/batches`), [cid])
  const [show, setShow] = useState(false)
  const [filter, setFilter] = useState('Semua')
  const [f, setF] = useState({ name: '', is_test: false, pdn_preset: 'Lokal' })
  const [err, setErr] = useState(null)
  const canCreate = role === 'admin' || role === 'operator'
  const counts = useMemo(() => {
    const c = { Semua: data?.length || 0 }
    ;(data || []).forEach((b) => { c[b.status] = (c[b.status] || 0) + 1 })
    return c
  }, [data])
  const rows = (data || []).filter((b) => filter === 'Semua' || b.status === filter)

  const create = async (e) => {
    e.preventDefault(); setErr(null)
    try { const b = await api(`${C(cid)}/batches`, { method: 'POST', body: f }); nav(`/c/${cid}/batch/${b.id}`) } catch (x) { setErr(x) }
  }
  const newBtn = canCreate && <button className="btn btn-primary" onClick={() => setShow(true)}><Plus className="h-4 w-4" /> Batch baru</button>

  if (loading) return <Loading />
  if (error) return <ErrorBox error={error} />
  return (
    <>
      <PageHeader title="Batch produk" subtitle="Satu batch boleh berisi banyak kategori. Isi, ajukan ke Reviewer, lalu ekspor zip setelah disetujui." actions={data.length > 0 && newBtn} />

      {data.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1.5" role="group" aria-label="Filter status">
          {FILTERS.filter((s) => s === 'Semua' || counts[s]).map((s) => (
            <button key={s} aria-pressed={filter === s}
              className={`rounded-full border px-3 py-1 text-sm font-semibold transition-colors duration-150 ${filter === s ? 'border-primary bg-primary text-on-primary' : 'border-line bg-card hover:bg-muted'}`}
              onClick={() => setFilter(s)}>
              {s} <span className={`num ml-1 text-xs ${filter === s ? 'text-white/80' : 'text-muted-fg'}`}>{counts[s] || 0}</span>
            </button>
          ))}
        </div>
      )}

      <div className="card overflow-x-auto">
        {data.length === 0 ? (
          <Empty icon={Boxes} title="Belum ada batch" action={newBtn}>
            {canCreate ? 'Buat batch pertama untuk mulai mengisi produk, menempel dari Excel, atau mengimpor form.' : 'Operator atau Admin Perusahaan yang membuat batch.'}
          </Empty>
        ) : (
          <table className="tbl">
            <thead><tr><th className="th">Batch</th><th className="th">Status</th><th className="th text-right">Produk</th><th className="th">Dibuat oleh</th><th className="th">Diperbarui</th></tr></thead>
            <tbody>
              {rows.map((b) => (
                <tr key={b.id}>
                  <td className="td">
                    <Link className="font-semibold text-primary hover:underline" to={`/c/${cid}/batch/${b.id}`}>{b.name}</Link>
                    {b.is_test && <span className="ml-2"><Chip tone="warn"><FlaskConical className="h-3 w-3" /> Uji coba</Chip></span>}
                  </td>
                  <td className="td"><Chip tone={statusTone(b.status)}>{b.status}</Chip></td>
                  <td className="td text-right num">{b.n_produk}</td>
                  <td className="td text-muted-fg">{b.dibuat_oleh}</td>
                  <td className="td whitespace-nowrap text-muted-fg">{new Date(b.updated_at).toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {show && (
        <Modal title="Batch baru" onClose={() => setShow(false)}>
          <form onSubmit={create} className="space-y-4">
            <ErrorBox error={err} />
            <div><label className="label" htmlFor="bn">Nama batch</label><input id="bn" className="input" required autoFocus placeholder="mis. Spare part Desember" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
            <div>
              <label className="label" htmlFor="bp">Asal produk</label>
              <select id="bp" className="input" value={f.pdn_preset} onChange={(e) => setF({ ...f, pdn_preset: e.target.value })}>
                <option value="Lokal">Lokal: diproduksi di Indonesia</option>
                <option value="Impor">Impor: tidak diproduksi di Indonesia</option>
              </select>
              <p className="mt-1.5 text-xs text-muted-fg">Mengisi kolom PDN otomatis. Bisa diubah per baris di grid.</p>
            </div>
            <label className="flex items-start gap-2.5 rounded-lg bg-warn-bg/60 p-3 text-sm">
              <input type="checkbox" className="mt-1" checked={f.is_test} onChange={(e) => setF({ ...f, is_test: e.target.checked })} />
              <span><b>Batch uji coba.</b> Nama produk diawali <code className="font-mono">[DUMMY]</code>. Hapus produk dari INAPROC segera setelah tes, karena status “Tidak Tayang” diabaikan INAPROC.</span>
            </label>
            <div className="flex justify-end gap-2"><button type="button" className="btn" onClick={() => setShow(false)}>Batal</button><button className="btn btn-primary">Buat batch</button></div>
          </form>
        </Modal>
      )}
    </>
  )
}
