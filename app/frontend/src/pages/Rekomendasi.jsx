import { useMemo, useState } from 'react'
import { Download, Search } from 'lucide-react'
import { api, C, download } from '../api.js'
import { useCompany } from '../company.js'
import { Chip, ErrorBox, Loading, PageHeader, useLoad } from '../components/ui.jsx'

const PR = { 1: 'Subkategori sudah diisi', 2: 'Kategori utama sudah diisi', 3: 'Kategori utama baru' }

export default function Rekomendasi() {
  const { cid } = useCompany()
  const { data, error, loading } = useLoad(() => api(`${C(cid)}/kelayakan/rekomendasi`), [cid])
  const [q, setQ] = useState('')
  const [pr, setPr] = useState(0)
  const rows = useMemo(() => (data || []).filter((r) => (!pr || r.prioritas === pr) && (!q || `${r.l1} ${r.l2} ${r.l3}`.toLowerCase().includes(q.toLowerCase()))), [data, q, pr])
  if (loading) return <Loading />
  if (error) return <ErrorBox error={error} />
  return (
    <>
      <PageHeader
        title="Rekomendasi Kategori"
        subtitle={`${data.length} kategori “Bisa” yang belum punya produk, diurutkan menurut prioritas.`}
        actions={<button className="btn" onClick={() => download(`${C(cid)}/kelayakan/export.xlsx`, 'rekap_kelayakan_kategori.xlsx')}><Download className="h-4 w-4" /> Ekspor Excel</button>}
      />
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="relative w-full max-w-sm">
          <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-fg" aria-hidden />
          <input className="input pl-8" placeholder="Cari…" aria-label="Cari rekomendasi" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="flex gap-1" role="group" aria-label="Filter prioritas">
          {[0, 1, 2, 3].map((p) => <button key={p} className={`btn btn-sm ${pr === p ? 'btn-primary' : ''}`} aria-pressed={pr === p} onClick={() => setPr(p)}>{p ? `Prioritas ${p}` : 'Semua'}</button>)}
        </div>
      </div>
      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead><tr><th className="th">Prioritas</th><th className="th">Kategori</th><th className="th">Jenis</th><th className="th">Catatan</th></tr></thead>
          <tbody className="divide-y divide-line">
            {rows.slice(0, 400).map((r) => (
              <tr key={r.id}>
                <td className="td whitespace-nowrap"><Chip tone={r.prioritas === 1 ? 'ok' : r.prioritas === 2 ? 'info' : 'mute'} icon={false}>P{r.prioritas}</Chip> <span className="text-xs text-muted-fg">{PR[r.prioritas]}</span></td>
                <td className="td"><div className="font-medium">{r.l3}</div><div className="text-xs text-muted-fg">{r.l1} › {r.l2}</div></td>
                <td className="td">{r.jenis === 'J' ? 'Jasa' : 'Barang'}</td>
                <td className="td text-xs">
                  {r.flags.map((f) => <div key={f} className="text-warn">⚠ {f}</div>)}
                  {!r.punya_template && <span className="text-muted-fg">Belum ada template — unduh di INAPROC</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length > 400 && <p className="p-3 text-xs text-muted-fg">Menampilkan 400 dari {rows.length}. Persempit dengan pencarian atau ekspor ke Excel.</p>}
      </div>
    </>
  )
}
