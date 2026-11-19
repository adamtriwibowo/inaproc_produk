import { Link } from 'react-router-dom'
import { AlertTriangle, ArrowRight, ListChecks, PackagePlus, Sparkles } from 'lucide-react'
import { api, C } from '../api.js'
import { useCompany } from '../company.js'
import { ErrorBox, Loading, PageHeader, Stat, useLoad } from '../components/ui.jsx'

// Urutan status batch adalah alur kerja yang sebenarnya, jadi ditampilkan sebagai tahapan.
const STEPS = [
  ['Draft', 'Sedang diisi'],
  ['Diajukan', 'Menunggu Reviewer'],
  ['Perlu Perbaikan', 'Dikembalikan'],
  ['Disetujui', 'Siap diekspor'],
  ['Diekspor', 'Zip dibuat'],
  ['Sudah Diunggah', 'Selesai di INAPROC'],
]
const fmt = (n) => Number(n).toLocaleString('id-ID')

export default function Dashboard() {
  const { cid, company, role } = useCompany()
  const { data, error, loading } = useLoad(() => api(`${C(cid)}/dashboard`), [cid])
  if (loading) return <Loading />
  if (error) return <ErrorBox error={error} />
  const k = data.kelayakan
  const pct = Math.round((k.kategori_bisa / Math.max(k.kategori_total, 1)) * 100)
  const canCreate = role === 'admin' || role === 'operator'
  const total = STEPS.reduce((n, [s]) => n + (data.batch[s] || 0), 0)

  return (
    <>
      <PageHeader title="Ringkasan" subtitle={`${company.name} · Institution ID ${company.institution_id}`} />

      <section className="card mb-5 overflow-hidden">
        <div className="grid gap-6 p-6 lg:grid-cols-[1fr_auto] lg:items-center">
          <div>
            <p className="text-[15px] text-muted-fg">Kategori yang bisa Anda isi sesuai KBLI perusahaan</p>
            <p className="num mt-1 text-[44px] font-bold leading-none tracking-tight">
              {fmt(k.kategori_bisa)} <span className="text-2xl font-semibold text-muted-fg">dari {fmt(k.kategori_total)}</span>
            </p>
            <div className="mt-4 flex h-3 overflow-hidden rounded-full bg-bad-bg" role="img" aria-label={`${pct}% kategori bisa diisi`}>
              <div className="h-full bg-ok transition-[width] duration-700" style={{ width: `${pct}%` }} />
            </div>
            <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm">
              <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-ok" aria-hidden />Bisa {fmt(k.kategori_bisa)} ({pct}%)</span>
              <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-bad-bg ring-1 ring-bad/30" aria-hidden />Tidak bisa {fmt(k.kategori_tidak_bisa)}</span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 lg:flex-col">
            {canCreate && <Link to={`/c/${cid}/batch`} className="btn btn-primary"><PackagePlus className="h-4 w-4" /> Buat batch produk</Link>}
            <Link to={`/c/${cid}/rekomendasi`} className="btn"><Sparkles className="h-4 w-4" /> Lihat rekomendasi</Link>
            <Link to={`/c/${cid}/kelayakan`} className="btn"><ListChecks className="h-4 w-4" /> Jelajahi kategori</Link>
          </div>
        </div>
      </section>

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Kategori utama yang terbuka" value={k.utama_dengan_bisa} hint={`${k.utama_bisa} bisa semua, ${k.utama_sebagian} sebagian`} />
        <Stat label="Subkategori bisa semua" value={k.sub_bisa} tone="ok" hint={`${k.sub_sebagian} sebagian, ${k.sub_tidak} tidak bisa`} />
        <Stat label="Produk sudah di INAPROC" value={fmt(data.produk_existing + data.produk_diunggah)} hint={`${data.produk_diunggah} dari batch di aplikasi`} />
        <Stat label="Batch berjalan" value={total} hint="semua status" />
      </div>

      <section className="card mb-6 p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-bold">Perjalanan batch</h2>
          <Link to={`/c/${cid}/batch`} className="flex items-center gap-1 text-sm font-semibold text-primary hover:underline">Semua batch <ArrowRight className="h-4 w-4" /></Link>
        </div>
        <ol className="grid gap-3 sm:grid-cols-3 xl:grid-cols-6">
          {STEPS.map(([s, desc], i) => {
            const n = data.batch[s] || 0
            return (
              <li key={s}>
                <Link to={`/c/${cid}/batch`} className={`relative block h-full rounded-lg border p-3 transition-colors duration-150 hover:border-primary ${n ? 'border-line bg-card' : 'border-dashed border-line bg-bg'}`}>
                  <div className="flex items-center gap-2 text-xs font-semibold text-muted-fg">
                    <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] ${n ? 'bg-primary text-on-primary' : 'bg-muted'}`}>{i + 1}</span>
                    {desc}
                  </div>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span className="num text-2xl font-bold">{n}</span>
                    <span className="text-sm font-semibold">{s}</span>
                  </div>
                </Link>
              </li>
            )
          })}
        </ol>
      </section>

      {data.peringatan_existing.length > 0 && (
        <section className="card border-warn/40 bg-warn-bg/40 p-5">
          <h2 className="mb-2 flex items-center gap-2 text-base font-bold text-warn">
            <AlertTriangle className="h-5 w-5" aria-hidden /> Produk existing di kategori yang kini tidak bisa diisi
          </h2>
          <ul className="space-y-1.5 text-sm">
            {data.peringatan_existing.map((w) => (
              <li key={w.l3}><b>{w.l3}</b>, {w.jumlah} produk <span className="text-muted-fg">({w.kategori.join('; ')})</span></li>
            ))}
          </ul>
          <p className="mt-3 text-sm text-muted-fg">KBLI di OSS mungkin berubah. Periksa ulang di menu KBLI perusahaan.</p>
        </section>
      )}
    </>
  )
}
