import { useMemo, useState } from 'react'
import { ChevronDown, ChevronRight, Download, Search } from 'lucide-react'
import { api, C, download } from '../api.js'
import { useCompany } from '../company.js'
import { Chip, ErrorBox, Loading, PageHeader, Stat, statusTone, useLoad } from '../components/ui.jsx'

const FILTERS = ['Semua', 'Bisa', 'Sebagian', 'Tidak Bisa']

export default function Kelayakan() {
  const { cid } = useCompany()
  const { data, error, loading } = useLoad(() => api(`${C(cid)}/kelayakan/tree`), [cid])
  const [q, setQ] = useState('')
  const [filter, setFilter] = useState('Semua')
  const [open, setOpen] = useState({})
  const [sel, setSel] = useState(null)
  const [detail, setDetail] = useState(null)

  const tree = useMemo(() => {
    if (!data) return []
    const ql = q.trim().toLowerCase()
    const out = []
    for (const n1 of data.tree) {
      if (filter !== 'Semua' && n1.status !== filter && !(filter === 'Bisa' && n1.ok > 0) && !(filter === 'Tidak Bisa' && n1.no > 0)) continue
      const subs = []
      for (const n2 of n1.children) {
        const leaves = n2.children.filter((c) => {
          if (filter === 'Bisa' && !c.ok) return false
          if (filter === 'Tidak Bisa' && c.ok) return false
          if (filter === 'Sebagian' && n2.status !== 'Sebagian') return false
          return !ql || `${n1.name} ${n2.name} ${c.name}`.toLowerCase().includes(ql)
        })
        if (leaves.length) subs.push({ ...n2, leaves })
      }
      if (subs.length) out.push({ ...n1, subs })
    }
    return out
  }, [data, q, filter])

  const pick = async (c) => {
    setSel(c.id); setDetail(null)
    try { setDetail(await api(`${C(cid)}/kelayakan/category/${c.id}`)) } catch (e) { setDetail({ error: e }) }
  }
  const forceOpen = q.trim().length > 1

  if (loading) return <Loading />
  if (error) return <ErrorBox error={error} />
  const t = data.totals
  return (
    <>
      <PageHeader
        title="Kelayakan kategori"
        subtitle="Kategori Bisa ⇔ ada KBLI perusahaan (kode dan versi) di daftar KBLI kategori."
        actions={<button className="btn" onClick={() => download(`${C(cid)}/kelayakan/export.xlsx`, 'rekap_kelayakan_kategori.xlsx')}><Download className="h-4 w-4" /> Ekspor Excel</button>}
      />
      <div className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Kategori produk bisa" value={t.kategori_bisa} tone="ok" />
        <Stat label="Kategori produk tidak bisa" value={t.kategori_tidak_bisa} tone="bad" />
        <Stat label="Subkategori" value={`${t.sub_bisa} / ${t.sub_sebagian} / ${t.sub_tidak}`} hint="bisa / sebagian / tidak bisa" />
        <Stat label="Kategori utama" value={`${t.utama_bisa} / ${t.utama_sebagian} / ${t.utama_tidak}`} hint="bisa / sebagian / tidak bisa" />
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="relative w-full max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-[11px] h-4 w-4 text-muted-fg" aria-hidden />
          <input className="input pl-9" placeholder="Cari kategori…" aria-label="Cari kategori" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter status">
          {FILTERS.map((f) => (
            <button key={f} className={`rounded-full border px-3 py-1 text-sm font-semibold transition-colors duration-150 ${filter === f ? 'border-primary bg-primary text-on-primary' : 'border-line bg-card hover:bg-muted'}`} aria-pressed={filter === f} onClick={() => setFilter(f)}>{f}</button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
        <div className="card divide-y divide-line">
          {tree.length === 0 && <div className="p-6 text-center text-sm text-muted-fg">Tidak ada kategori yang cocok.</div>}
          {tree.map((n1) => {
            const o1 = forceOpen || open[n1.name]
            return (
              <div key={n1.name}>
                <button className="flex w-full items-center gap-2 px-4 py-3 text-left transition-colors duration-150 hover:bg-muted" onClick={() => setOpen({ ...open, [n1.name]: !open[n1.name] })} aria-expanded={!!o1}>
                  {o1 ? <ChevronDown className="h-4 w-4" aria-hidden /> : <ChevronRight className="h-4 w-4" aria-hidden />}
                  <span className="flex-1 text-[15px] font-bold">{n1.name}</span>
                  <span className="num text-xs text-muted-fg">{n1.ok}/{n1.ok + n1.no}</span>
                  <Chip tone={statusTone(n1.status)}>{n1.status}</Chip>
                </button>
                {o1 && n1.subs.map((n2) => {
                  const k2 = n1.name + '»' + n2.name
                  const o2 = forceOpen || open[k2]
                  return (
                    <div key={k2} className="border-t border-line/60 bg-bg/50">
                      <button className="flex w-full items-center gap-2 py-2 pl-10 pr-4 text-left transition-colors duration-150 hover:bg-muted" onClick={() => setOpen({ ...open, [k2]: !open[k2] })} aria-expanded={!!o2}>
                        {o2 ? <ChevronDown className="h-3.5 w-3.5" aria-hidden /> : <ChevronRight className="h-3.5 w-3.5" aria-hidden />}
                        <span className="flex-1 text-sm font-medium">{n2.name}</span>
                        <span className="num text-xs text-muted-fg">{n2.ok}/{n2.ok + n2.no}</span>
                        <Chip tone={statusTone(n2.status)}>{n2.status}</Chip>
                      </button>
                      {o2 && n2.leaves.map((c) => (
                        <button key={c.id} onClick={() => pick(c)} aria-pressed={sel === c.id}
                          className={`flex w-full items-center gap-2 py-2 pl-16 pr-4 text-left text-sm transition-colors duration-150 hover:bg-muted ${sel === c.id ? 'bg-primary/10' : ''}`}>
                          <span className="flex-1">{c.name}</span>
                          {c.existing > 0 && <span className="font-mono text-xs text-muted-fg">{c.existing} produk</span>}
                          {c.ok && c.punya_template && <Chip tone="info" icon={false}>Template</Chip>}
                          <Chip tone={c.ok ? 'ok' : 'bad'}>{c.ok ? 'Bisa' : 'Tidak Bisa'}</Chip>
                        </button>
                      ))}
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>

        <aside className="card h-fit p-4 lg:sticky lg:top-6" aria-live="polite">
          {!sel && <p className="text-sm text-muted-fg">Pilih kategori produk untuk melihat KBLI yang diterima.</p>}
          {sel && !detail && <Loading />}
          {detail?.error && <ErrorBox error={detail.error} />}
          {detail && !detail.error && (
            <div className="space-y-3">
              <div>
                <div className="text-xs text-muted-fg">{detail.l1} › {detail.l2}</div>
                <h2 className="text-base font-semibold">{detail.l3}</h2>
                <div className="mt-1 flex flex-wrap gap-1">
                  <Chip tone={detail.ok ? 'ok' : 'bad'}>{detail.ok ? 'Bisa' : 'Tidak Bisa'}</Chip>
                  <Chip>{detail.jenis === 'J' ? 'Jasa' : detail.jenis === 'B' ? 'Barang' : detail.jenis}</Chip>
                  {detail.punya_template && <Chip tone="info" icon={false}>Template tersedia</Chip>}
                </div>
              </div>
              {detail.catatan && <p className="rounded-md bg-warn-bg p-2 text-xs text-warn">{detail.catatan}</p>}
              {detail.flags.map((f) => <p key={f} className="rounded-md bg-warn-bg p-2 text-xs text-warn">{f}</p>)}
              <div>
                <h3 className="mb-1 text-[13px] font-semibold text-muted-fg">KBLI perusahaan yang cocok</h3>
                {detail.kbli_cocok.length === 0 ? <p className="text-sm text-bad">Tidak ada KBLI perusahaan yang cocok.</p> : (
                  <ul className="text-sm">{detail.kbli_cocok.map((k) => <li key={k.code + k.version}><span className="font-mono">{k.code}</span> ({k.version}) {k.name}</li>)}</ul>
                )}
              </div>
              <div>
                <h3 className="mb-1 text-[13px] font-semibold text-muted-fg">KBLI yang diterima kategori ({detail.kbli.length})</h3>
                <ul className="max-h-64 overflow-auto text-xs">
                  {detail.kbli.map((k) => (
                    <li key={k.code + k.version} className={`py-0.5 ${k.milik ? 'font-semibold text-ok' : ''}`}>
                      <span className="font-mono">{k.code}</span> <span className="text-muted-fg">({k.version})</span> {k.name} {k.milik && '✓ milik perusahaan'}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </aside>
      </div>
    </>
  )
}
