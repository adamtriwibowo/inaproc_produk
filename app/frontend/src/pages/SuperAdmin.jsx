import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import { Chip, ErrorBox, Loading, PageHeader, useLoad, useToast } from '../components/ui.jsx'

const ROLES = { admin: 'Admin Perusahaan', operator: 'Operator Input', reviewer: 'Reviewer' }

export default function SuperAdmin() {
  const { me, refresh } = useAuth()
  const toast = useToast()
  const ov = useLoad(() => api('/admin/overview'), [])
  const users = useLoad(() => api('/admin/users'), [])
  const comps = useLoad(() => api('/admin/companies'), [])
  const [err, setErr] = useState(null)
  const [c, setC] = useState({ name: '', store_name: '', inaproc_email: '', institution_id: '', scale: '' })
  const [u, setU] = useState({ email: '', name: '', password: '' })
  const [m, setM] = useState({ user_id: '', company_id: '', role: 'operator' })

  if (!me.user.is_super) return <Navigate to="/" replace />
  const run = async (fn, okMsg) => {
    setErr(null)
    try { await fn(); toast(okMsg); ov.reload(); users.reload(); comps.reload(); refresh() } catch (x) { setErr(x) }
  }
  const cname = (id) => comps.data?.find((x) => x.id === id)?.name || id

  return (
    <div className="mx-auto max-w-[1200px] p-4">
      <PageHeader title="Super Admin" subtitle="Perusahaan, pengguna, dan hak akses lintas perusahaan." actions={<Link to="/" className="btn"><ArrowLeft className="h-4 w-4" /> Kembali</Link>} />
      <ErrorBox error={err} />

      <section className="card mb-4">
        <h2 className="border-b border-line px-3 py-2 font-semibold">Ringkasan lintas perusahaan</h2>
        {ov.loading ? <Loading /> : (
          <table className="w-full">
            <thead><tr><th className="th">Perusahaan</th><th className="th text-right">Bisa</th><th className="th text-right">Tidak Bisa</th><th className="th">Batch</th><th className="th">Status</th></tr></thead>
            <tbody className="divide-y divide-line">
              {ov.data.map((o) => (
                <tr key={o.id}>
                  <td className="td font-medium"><Link className="text-primary hover:underline" to={`/c/${o.id}`}>{o.name}</Link></td>
                  <td className="td text-right font-mono">{o.kategori_bisa}</td><td className="td text-right font-mono">{o.kategori_tidak_bisa}</td>
                  <td className="td text-xs">{Object.entries(o.batch).map(([k, v]) => `${k}: ${v}`).join(' · ') || '—'}</td>
                  <td className="td"><Chip tone={o.active ? 'ok' : 'mute'}>{o.active ? 'Aktif' : 'Nonaktif'}</Chip></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="card p-4">
          <h2 className="mb-3 font-semibold">Perusahaan</h2>
          <ul className="mb-3 divide-y divide-line text-sm">
            {comps.data?.map((x) => (
              <li key={x.id} className="flex items-center justify-between py-1.5">
                <span>{x.name} <span className="font-mono text-xs text-muted-fg">{x.institution_id}</span></span>
                <button className="btn btn-sm" onClick={() => run(() => api(`/admin/companies/${x.id}`, { method: 'PATCH', body: { active: !x.active } }), 'Status diubah')}>{x.active ? 'Nonaktifkan' : 'Aktifkan'}</button>
              </li>
            ))}
          </ul>
          <form className="grid grid-cols-2 gap-2" onSubmit={(e) => { e.preventDefault(); run(() => api('/admin/companies', { method: 'POST', body: c }), 'Perusahaan dibuat').then(() => setC({ name: '', store_name: '', inaproc_email: '', institution_id: '', scale: '' })) }}>
            <div><label className="label" htmlFor="cn">Nama perusahaan</label><input id="cn" className="input" required value={c.name} onChange={(e) => setC({ ...c, name: e.target.value })} /></div>
            <div><label className="label" htmlFor="cs">Nama toko INAPROC</label><input id="cs" className="input" value={c.store_name} onChange={(e) => setC({ ...c, store_name: e.target.value })} /></div>
            <div><label className="label" htmlFor="ce">Akun/email INAPROC (teks)</label><input id="ce" className="input" value={c.inaproc_email} onChange={(e) => setC({ ...c, inaproc_email: e.target.value })} /></div>
            <div><label className="label" htmlFor="ci">Institution ID</label><input id="ci" className="input font-mono" required value={c.institution_id} onChange={(e) => setC({ ...c, institution_id: e.target.value })} /></div>
            <div><label className="label" htmlFor="csc">Skala usaha</label><input id="csc" className="input" value={c.scale} onChange={(e) => setC({ ...c, scale: e.target.value })} /></div>
            <div className="flex items-end"><button className="btn btn-primary w-full">Buat perusahaan</button></div>
          </form>
          <p className="mt-2 text-xs text-muted-fg">Jangan menyimpan password INAPROC di sini. Setelah dibuat, Admin Perusahaan menambahkan KBLI dan mengunggah template.</p>
        </section>

        <section className="card p-4">
          <h2 className="mb-3 font-semibold">Pengguna & akses</h2>
          <ul className="mb-3 max-h-64 divide-y divide-line overflow-auto text-sm">
            {users.data?.map((x) => (
              <li key={x.id} className="py-1.5">
                <div className="flex items-center justify-between">
                  <span>{x.email} {x.is_super && <Chip tone="info" icon={false}>Super Admin</Chip>}</span>
                  <button className="btn btn-sm" onClick={() => run(() => api(`/admin/users/${x.id}`, { method: 'PATCH', body: { active: !x.active } }), 'Status diubah')}>{x.active ? 'Nonaktifkan' : 'Aktifkan'}</button>
                </div>
                <div className="mt-0.5 flex flex-wrap gap-1">
                  {x.memberships.map((mm) => (
                    <span key={mm.company_id} className="chip bg-muted text-muted-fg">
                      {cname(mm.company_id)}: {ROLES[mm.role]}
                      <button aria-label="Cabut akses" className="ml-1 text-bad" onClick={() => run(() => api(`/admin/memberships?user_id=${x.id}&company_id=${mm.company_id}`, { method: 'DELETE' }), 'Akses dicabut')}>×</button>
                    </span>
                  ))}
                </div>
              </li>
            ))}
          </ul>
          <form className="mb-4 grid grid-cols-2 gap-2" onSubmit={(e) => { e.preventDefault(); run(() => api('/admin/users', { method: 'POST', body: u }), 'Pengguna dibuat').then(() => setU({ email: '', name: '', password: '' })) }}>
            <div><label className="label" htmlFor="ue">Email</label><input id="ue" type="email" className="input" required value={u.email} onChange={(e) => setU({ ...u, email: e.target.value })} /></div>
            <div><label className="label" htmlFor="un">Nama</label><input id="un" className="input" value={u.name} onChange={(e) => setU({ ...u, name: e.target.value })} /></div>
            <div><label className="label" htmlFor="up">Password awal (min. 8)</label><input id="up" type="password" minLength={8} required autoComplete="new-password" className="input" value={u.password} onChange={(e) => setU({ ...u, password: e.target.value })} /></div>
            <div className="flex items-end"><button className="btn btn-primary w-full">Undang pengguna</button></div>
          </form>
          <h3 className="mb-2 text-sm font-semibold">Beri akses perusahaan</h3>
          <form className="grid grid-cols-3 gap-2" onSubmit={(e) => { e.preventDefault(); run(() => api('/admin/memberships', { method: 'PUT', body: { user_id: Number(m.user_id), company_id: Number(m.company_id), role: m.role } }), 'Akses disimpan') }}>
            <select aria-label="Pengguna" className="input" required value={m.user_id} onChange={(e) => setM({ ...m, user_id: e.target.value })}><option value="">Pengguna…</option>{users.data?.map((x) => <option key={x.id} value={x.id}>{x.email}</option>)}</select>
            <select aria-label="Perusahaan" className="input" required value={m.company_id} onChange={(e) => setM({ ...m, company_id: e.target.value })}><option value="">Perusahaan…</option>{comps.data?.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select>
            <select aria-label="Peran" className="input" value={m.role} onChange={(e) => setM({ ...m, role: e.target.value })}>{Object.entries(ROLES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
            <button className="btn btn-primary col-span-3">Simpan akses</button>
          </form>
        </section>
      </div>
    </div>
  )
}
