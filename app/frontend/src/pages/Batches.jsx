import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FlaskConical, Plus } from 'lucide-react'
import { api, C } from '../api.js'
import { useCompany } from '../company.js'
import { Chip, Empty, ErrorBox, Loading, Modal, PageHeader, statusTone, useLoad } from '../components/ui.jsx'

export default function Batches() {
  const { cid, role } = useCompany()
  const nav = useNavigate()
  const { data, error, loading } = useLoad(() => api(`${C(cid)}/batches`), [cid])
  const [show, setShow] = useState(false)
  const [f, setF] = useState({ name: '', is_test: false, pdn_preset: 'Lokal' })
  const [err, setErr] = useState(null)
  const canCreate = role === 'admin' || role === 'operator'

  const create = async (e) => {
    e.preventDefault(); setErr(null)
    try { const b = await api(`${C(cid)}/batches`, { method: 'POST', body: f }); nav(`/c/${cid}/batch/${b.id}`) } catch (x) { setErr(x) }
  }
  if (loading) return <Loading />
  if (error) return <ErrorBox error={error} />
  return (
    <>
      <PageHeader title="Batch Produk" subtitle="Satu batch boleh berisi banyak kategori."
        actions={canCreate && <button className="btn btn-primary" onClick={() => setShow(true)}><Plus className="h-4 w-4" /> Batch baru</button>} />
      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead><tr><th className="th">Batch</th><th className="th">Status</th><th className="th text-right">Produk</th><th className="th">Dibuat oleh</th><th className="th">Diperbarui</th></tr></thead>
          <tbody className="divide-y divide-line">
            {data.map((b) => (
              <tr key={b.id} className="hover:bg-muted/50">
                <td className="td"><Link className="font-medium text-primary hover:underline" to={`/c/${cid}/batch/${b.id}`}>{b.name}</Link>{b.is_test && <span className="ml-2"><Chip tone="warn"><FlaskConical className="h-3 w-3" /> Uji coba</Chip></span>}</td>
                <td className="td"><Chip tone={statusTone(b.status)}>{b.status}</Chip></td>
                <td className="td text-right font-mono">{b.n_produk}</td>
                <td className="td text-xs">{b.dibuat_oleh}</td>
                <td className="td text-xs text-muted-fg">{new Date(b.updated_at).toLocaleString('id-ID')}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data.length === 0 && <Empty>Belum ada batch.</Empty>}
      </div>

      {show && (
        <Modal title="Batch baru" onClose={() => setShow(false)}>
          <form onSubmit={create} className="space-y-3">
            <ErrorBox error={err} />
            <div><label className="label" htmlFor="bn">Nama batch</label><input id="bn" className="input" required autoFocus value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
            <div>
              <label className="label" htmlFor="bp">Preset PDN</label>
              <select id="bp" className="input" value={f.pdn_preset} onChange={(e) => setF({ ...f, pdn_preset: e.target.value })}>
                <option value="Lokal">Lokal — diproduksi di Indonesia</option>
                <option value="Impor">Impor — tidak diproduksi di Indonesia</option>
              </select>
              <p className="mt-1 text-xs text-muted-fg">Bisa diubah per baris di grid.</p>
            </div>
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox" className="mt-1" checked={f.is_test} onChange={(e) => setF({ ...f, is_test: e.target.checked })} />
              <span><b>Batch uji coba</b> — nama produk diberi awalan <code className="font-mono">[DUMMY]</code>. Hapus produk dari INAPROC segera setelah tes (status “Tidak Tayang” diabaikan INAPROC).</span>
            </label>
            <div className="flex justify-end gap-2"><button type="button" className="btn" onClick={() => setShow(false)}>Batal</button><button className="btn btn-primary">Buat batch</button></div>
          </form>
        </Modal>
      )}
    </>
  )
}
