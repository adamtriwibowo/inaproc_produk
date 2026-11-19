import { useState } from 'react'
import { Trash2 } from 'lucide-react'
import { api, C } from '../api.js'
import { useCompany } from '../company.js'
import { ErrorBox, Loading, PageHeader, useLoad, useToast } from '../components/ui.jsx'

export const ROLES = { admin: 'Admin Perusahaan', operator: 'Operator Input', reviewer: 'Reviewer' }

export default function Members() {
  const { cid, role } = useCompany()
  const toast = useToast()
  const { data, error, loading, reload } = useLoad(() => (role === 'admin' ? api(`${C(cid)}/members`) : Promise.resolve([])), [cid, role])
  const [f, setF] = useState({ email: '', role: 'operator' })
  const [err, setErr] = useState(null)
  if (role !== 'admin') return <ErrorBox error={{ message: 'Hanya Admin Perusahaan yang bisa mengelola anggota.' }} />
  if (loading) return <Loading />
  if (error) return <ErrorBox error={error} />

  const save = async (e, email = f.email, r = f.role) => {
    e?.preventDefault(); setErr(null)
    try { await api(`${C(cid)}/members`, { method: 'PUT', body: { email, role: r } }); toast('Anggota disimpan'); if (e) setF({ email: '', role: 'operator' }); reload() } catch (x) { setErr(x) }
  }
  const del = async (m) => {
    if (!confirm(`Cabut akses ${m.email}?`)) return
    try { await api(`${C(cid)}/members/${m.user_id}`, { method: 'DELETE' }); reload() } catch (x) { setErr(x) }
  }
  return (
    <>
      <PageHeader title="Anggota perusahaan" subtitle="Peran berlaku hanya di perusahaan ini. Pengguna baru diundang oleh Super Admin." />
      <ErrorBox error={err} />
      <div className="card overflow-x-auto">
        <table className="tbl">
          <thead><tr><th className="th">Email</th><th className="th">Nama</th><th className="th">Peran</th><th className="th"><span className="sr-only">Aksi</span></th></tr></thead>
          <tbody className="divide-y divide-line">
            {data.map((m) => (
              <tr key={m.user_id}>
                <td className="td">{m.email}</td><td className="td">{m.name}</td>
                <td className="td">
                  <select className="input w-44" aria-label={`Peran ${m.email}`} value={m.role} onChange={(e) => save(null, m.email, e.target.value)}>
                    {Object.entries(ROLES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </td>
                <td className="td"><button className="btn btn-sm" aria-label={`Cabut ${m.email}`} onClick={() => del(m)}><Trash2 className="h-3.5 w-3.5" /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <form onSubmit={save} className="flex flex-wrap items-end gap-2 border-t border-line p-3">
          <div className="min-w-[220px] flex-1"><label className="label" htmlFor="me">Email pengguna terdaftar</label><input id="me" type="email" required className="input" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></div>
          <div className="w-48"><label className="label" htmlFor="mr">Peran</label><select id="mr" className="input" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>{Object.entries(ROLES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
          <button className="btn btn-primary">Tambah / ubah</button>
        </form>
      </div>
    </>
  )
}
