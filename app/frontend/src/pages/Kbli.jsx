import { useRef, useState } from 'react'
import { Plus, Trash2, Upload } from 'lucide-react'
import { api, C } from '../api.js'
import { useCompany } from '../company.js'
import { ErrorBox, Loading, PageHeader, useLoad, useToast, Chip } from '../components/ui.jsx'

export default function Kbli() {
  const { cid, role } = useCompany()
  const toast = useToast()
  const { data, error, loading, reload } = useLoad(() => api(`${C(cid)}/kbli`), [cid])
  const [f, setF] = useState({ code: '', version: '2020', name: '' })
  const [err, setErr] = useState(null)
  const fileRef = useRef(null)
  const admin = role === 'admin'

  const add = async (e) => {
    e.preventDefault(); setErr(null)
    try { await api(`${C(cid)}/kbli`, { method: 'POST', body: f }); setF({ code: '', version: '2020', name: '' }); toast('KBLI ditambahkan'); reload() } catch (x) { setErr(x) }
  }
  const del = async (k) => {
    if (!confirm(`Hapus KBLI ${k.code} (${k.version})? Kelayakan kategori akan dihitung ulang.`)) return
    try { await api(`${C(cid)}/kbli/${k.id}`, { method: 'DELETE' }); reload() } catch (x) { setErr(x) }
  }
  const importCheck = async (e) => {
    const file = e.target.files[0]; if (!file) return
    setErr(null)
    const form = new FormData(); form.append('file', file)
    try { const r = await api(`${C(cid)}/kbli/import-check`, { method: 'POST', form }); toast(`Impor berhasil: ${r.kategori_diperbarui} kategori dicocokkan`); reload() } catch (x) { setErr(x) }
    e.target.value = ''
  }

  if (loading) return <Loading />
  if (error) return <ErrorBox error={error} />
  return (
    <>
      <PageHeader
        title="KBLI perusahaan"
        subtitle="KBLI perusahaan dan KBLI yang paling banyak membuka kategori “Tidak Bisa”."
        actions={admin && (
          <>
            <input ref={fileRef} type="file" accept=".json,application/json" hidden onChange={importCheck} />
            <button className="btn" onClick={() => fileRef.current.click()}><Upload className="h-4 w-4" /> Impor inaproc_kbli_check.json</button>
          </>
        )}
      />
      {admin && <p className="mb-3 rounded-md bg-primary/10 p-2.5 text-sm text-primary">Jalankan <code className="font-mono">scripts/browser_snippets.js</code> di DevTools saat login ke akun INAPROC <b>perusahaan ini</b>, lalu impor file hasilnya. <code className="font-mono">institutionId</code> di file harus sama dengan perusahaan aktif.</p>}
      <ErrorBox error={err} />
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="card">
          <h2 className="border-b border-line px-4 py-3 text-base font-bold">KBLI perusahaan ({data.kbli.length})</h2>
          <table className="tbl">
            <thead><tr><th className="th">Kode</th><th className="th">Versi</th><th className="th">Nama</th><th className="th text-right">Kategori dibuka</th>{admin && <th className="th"><span className="sr-only">Aksi</span></th>}</tr></thead>
            <tbody className="divide-y divide-line">
              {data.kbli.map((k) => (
                <tr key={k.id}>
                  <td className="td font-mono">{k.code}</td><td className="td">{k.version}</td><td className="td">{k.name}</td>
                  <td className="td text-right num">{k.kategori_dibuka === 0 ? <Chip tone="warn">0</Chip> : k.kategori_dibuka}</td>
                  {admin && <td className="td"><button className="btn btn-sm" aria-label={`Hapus KBLI ${k.code}`} onClick={() => del(k)}><Trash2 className="h-3.5 w-3.5" /></button></td>}
                </tr>
              ))}
            </tbody>
          </table>
          {admin && (
            <form onSubmit={add} className="flex flex-wrap items-end gap-2 border-t border-line p-3">
              <div className="w-28"><label className="label" htmlFor="kc">Kode</label><input id="kc" className="input font-mono" required value={f.code} onChange={(e) => setF({ ...f, code: e.target.value })} /></div>
              <div className="w-24"><label className="label" htmlFor="kv">Versi</label><select id="kv" className="input" value={f.version} onChange={(e) => setF({ ...f, version: e.target.value })}><option>2020</option><option>2025</option></select></div>
              <div className="min-w-[160px] flex-1"><label className="label" htmlFor="kn">Nama (opsional)</label><input id="kn" className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
              <button className="btn btn-primary"><Plus className="h-4 w-4" /> Tambah</button>
            </form>
          )}
        </section>

        <section className="card">
          <h2 className="border-b border-line px-4 py-3 text-base font-bold">KBLI yang paling banyak membuka kategori terkunci</h2>
          <p className="px-3 pt-2 text-xs text-muted-fg">Menambah KBLI ini (bila relevan dengan usaha Anda di OSS) akan membuka kategori terbanyak.</p>
          <table className="tbl">
            <thead><tr><th className="th">Kode</th><th className="th">Versi</th><th className="th">Nama</th><th className="th text-right">Kategori</th></tr></thead>
            <tbody className="divide-y divide-line">
              {data.ranking_tidak_bisa.map((k) => (
                <tr key={k.code + k.version}><td className="td font-mono">{k.code}</td><td className="td">{k.version}</td><td className="td">{k.name}</td><td className="td text-right num">{k.kategori}</td></tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </>
  )
}
