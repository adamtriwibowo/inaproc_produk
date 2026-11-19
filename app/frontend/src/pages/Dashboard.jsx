import { Link } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'
import { api, C } from '../api.js'
import { useCompany } from '../company.js'
import { Chip, ErrorBox, Loading, PageHeader, Stat, statusTone, useLoad } from '../components/ui.jsx'

const ORDER = ['Draft', 'Diajukan', 'Perlu Perbaikan', 'Disetujui', 'Diekspor', 'Sudah Diunggah']

export default function Dashboard() {
  const { cid, company } = useCompany()
  const { data, error, loading } = useLoad(() => api(`${C(cid)}/dashboard`), [cid])
  if (loading) return <Loading />
  if (error) return <ErrorBox error={error} />
  const k = data.kelayakan
  return (
    <>
      <PageHeader title="Ringkasan" subtitle={`${company.name} · Institution ID ${company.institution_id}`} />
      <h2 className="mb-2 text-sm font-semibold text-muted-fg">Kelayakan kategori (berdasarkan KBLI perusahaan ini)</h2>
      <div className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Kategori Bisa" value={k.kategori_bisa} tone="ok" hint={`dari ${k.kategori_total} kategori produk`} />
        <Stat label="Kategori Tidak Bisa" value={k.kategori_tidak_bisa} tone="bad" />
        <Stat label="Kategori utama punya ≥1 Bisa" value={k.utama_dengan_bisa} hint={`${k.utama_bisa} bisa semua · ${k.utama_sebagian} sebagian`} />
        <Stat label="Produk sudah di INAPROC" value={data.produk_existing + data.produk_diunggah} hint={`${data.produk_diunggah} dari batch di aplikasi`} />
      </div>

      <h2 className="mb-2 text-sm font-semibold text-muted-fg">Batch per status</h2>
      <div className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-6">
        {ORDER.map((s) => (
          <Link key={s} to={`/c/${cid}/batch`} className="card p-3 transition-colors duration-200 hover:border-primary">
            <Chip tone={statusTone(s)} icon={false}>{s}</Chip>
            <div className="mt-2 font-mono text-2xl font-semibold">{data.batch[s] || 0}</div>
          </Link>
        ))}
      </div>

      {data.peringatan_existing.length > 0 && (
        <div className="card border-warn/40 p-4">
          <h2 className="mb-2 flex items-center gap-2 font-semibold text-warn">
            <AlertTriangle className="h-4 w-4" aria-hidden /> Produk existing di kategori yang kini “Tidak Bisa”
          </h2>
          <ul className="space-y-1 text-sm">
            {data.peringatan_existing.map((w) => (
              <li key={w.l3}><b>{w.l3}</b> · {w.jumlah} produk <span className="text-muted-fg">({w.kategori.join('; ')})</span></li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-muted-fg">KBLI di OSS mungkin berubah. Periksa ulang lewat menu KBLI.</p>
        </div>
      )}
    </>
  )
}
