import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, KeyRound, Plus, ShieldAlert, Trash2 } from 'lucide-react'
import { api, C } from '../api.js'
import { useCompany } from '../company.js'
import { Chip, ErrorBox, Loading, PageHeader, Spinner, useLoad, useToast } from '../components/ui.jsx'

const SCOPE = { semua: 'Semua kategori', l1: 'Kategori utama', l2: 'Subkategori', l3: 'Kategori produk' }
const usd = (n) => (n == null ? '—' : `US$ ${Number(n).toFixed(n < 1 ? 4 : 2)}`)

function Section({ title, desc, children }) {
  return (
    <section className="card mb-5 p-5 lg:p-6">
      <h2 className="text-base font-bold">{title}</h2>
      {desc && <p className="mb-4 mt-1 text-sm text-muted-fg">{desc}</p>}
      {!desc && <div className="mb-3" />}
      {children}
    </section>
  )
}

export function QuotaBar({ q }) {
  if (!q) return null
  const pct = q.pct ?? 0
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="font-medium">Pemakaian bulan ini</span>
        <span className="num text-muted-fg">{usd(q.spend_usd)}{q.quota_usd != null ? ` dari ${usd(q.quota_usd)}` : ' (tanpa kuota)'}</span>
      </div>
      {q.quota_usd != null && (
        <div className="h-2.5 overflow-hidden rounded-full bg-muted" role="img" aria-label={`${pct}% kuota terpakai`}>
          <div className={`h-full ${q.exhausted ? 'bg-bad' : q.warn ? 'bg-warn' : 'bg-ok'}`} style={{ width: `${Math.min(pct, 100)}%` }} />
        </div>
      )}
      {q.warn && <p className="mt-1.5 flex items-center gap-1.5 text-sm text-warn"><AlertTriangle className="h-4 w-4" aria-hidden />{q.exhausted ? 'Kuota habis. Fitur AI berhenti; input manual dan foto lokal tetap jalan.' : 'Pemakaian sudah di atas 80% kuota.'}</p>}
    </div>
  )
}

export default function AiSettings() {
  const { cid } = useCompany()
  const toast = useToast()
  const st = useLoad(() => api(`${C(cid)}/ai/settings`), [cid])
  const rules = useLoad(() => api(`${C(cid)}/ai/pricing-rules`), [cid])
  const usage = useLoad(() => api(`${C(cid)}/ai/usage`), [cid])
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState('')
  const [key, setKey] = useState('')
  const [slots, setSlots] = useState(null)
  const [other, setOther] = useState({ quota: '', pattern: '', noRet: false })
  const [models, setModels] = useState({})
  const [rule, setRule] = useState({ scope: 'semua', category_name: '', markup_pct: 20, rounding: 1000, min_price: 0 })

  useEffect(() => {
    if (!st.data) return
    setSlots(st.data.slots)
    setOther({ quota: st.data.quota_usd ?? '', pattern: st.data.name_pattern, noRet: st.data.no_data_retention })
    if (st.data.has_key || st.data.key_source !== 'belum ada') {
      Object.keys(st.data.slots).forEach((s) => api(`${C(cid)}/ai/models?slot=${s}`).then((m) => setModels((x) => ({ ...x, [s]: m }))).catch(() => {}))
    }
  }, [st.data, cid])

  const priceOf = useMemo(() => (slot, id) => models[slot]?.find((m) => m.id === id), [models])
  const run = async (name, fn, ok) => {
    setErr(null); setBusy(name)
    try { await fn(); toast(ok); st.reload(); usage.reload() } catch (x) { setErr(x) } finally { setBusy('') }
  }
  const put = (body) => api(`${C(cid)}/ai/settings`, { method: 'PUT', body })

  if (st.loading || !slots) return <Loading />
  if (st.error) return <ErrorBox error={st.error} />
  const d = st.data
  const hasKey = d.key_source !== 'belum ada'

  return (
    <>
      <PageHeader title="Pengaturan AI" subtitle="Agen AI hanya membuat draf. Manusia tetap memverifikasi, karena produk hasil unggah langsung tayang dan tidak bisa dibatalkan." />
      <ErrorBox error={err} />

      <div className="mb-5 grid gap-5 lg:grid-cols-[1fr_1fr]">
        <Section title="API key OpenRouter" desc="Buat key di openrouter.ai/keys. Key disimpan terenkripsi di server dan tidak pernah ditampilkan lagi.">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Chip tone={hasKey ? 'ok' : 'warn'}>{hasKey ? `Key aktif (${d.key_source})` : 'Belum ada key'}</Chip>
          </div>
          <label className="label" htmlFor="ak">Key baru {d.has_key ? '(mengganti key perusahaan)' : '(khusus perusahaan ini; kosongkan bila memakai key organisasi)'}</label>
          <div className="flex gap-2">
            <input id="ak" type="password" autoComplete="off" className="input font-mono" placeholder="sk-or-…" value={key} onChange={(e) => setKey(e.target.value)} />
            <button className="btn btn-primary shrink-0" disabled={!key.trim() || busy === 'key'} onClick={() => run('key', async () => { await put({ api_key: key.trim() }); setKey('') }, 'Key disimpan')}>
              {busy === 'key' ? <Spinner /> : <KeyRound className="h-4 w-4" />} Simpan
            </button>
          </div>
          {d.has_key && <button className="mt-2 text-sm font-semibold text-bad hover:underline" onClick={() => confirm('Hapus key perusahaan? Fitur AI memakai key organisasi bila ada.') && run('key', () => put({ clear_key: true }), 'Key dihapus')}>Hapus key perusahaan</button>}
        </Section>

        <Section title="Kuota & privasi">
          <QuotaBar q={d.kuota_status} />
          <div className="mt-4">
            <label className="label" htmlFor="q">Kuota bulanan (USD)</label>
            <input id="q" type="number" min="0" step="0.5" className="input" placeholder="Tanpa batas" value={other.quota} onChange={(e) => setOther({ ...other, quota: e.target.value })} />
          </div>
          <label className="mt-3 flex items-start gap-2.5 text-sm">
            <input type="checkbox" className="mt-1" checked={other.noRet} onChange={(e) => setOther({ ...other, noRet: e.target.checked })} />
            <span>Hanya pakai provider yang <b>tidak menyimpan data</b> (bila tersedia untuk model itu).</span>
          </label>
          <div className="mt-3 flex gap-2 rounded-lg bg-warn-bg/60 p-3 text-sm text-warn"><ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />{d.privasi}</div>
          <button className="btn btn-primary mt-4" disabled={busy === 'misc'} onClick={() => run('misc', () => put(other.quota === '' ? { clear_quota: true, no_data_retention: other.noRet } : { quota_usd: Number(other.quota), no_data_retention: other.noRet }), 'Pengaturan disimpan')}>Simpan kuota & privasi</button>
        </Section>
      </div>

      <Section title="Model per slot" desc="Model divalidasi ke OpenRouter saat disimpan: harus mendukung kebutuhan slotnya (output terstruktur, tools, input gambar, atau output gambar). Harga diambil dari OpenRouter.">
        {!hasKey && <p className="mb-3 text-sm text-muted-fg">Isi API key dulu agar daftar model dan harganya bisa dimuat.</p>}
        <div className="space-y-4">
          {Object.entries(slots).map(([slot, v]) => {
            const p = priceOf(slot, v.model)
            return (
              <div key={slot} className="rounded-lg border border-line p-4">
                <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
                  <h3 className="text-sm font-bold">{d.slot_labels[slot]}</h3>
                  <span className="text-xs text-muted-fg">{p ? `US$ ${p.input_per_1m ?? '?'}/1M masuk · ${p.output_per_1m ?? '?'}/1M keluar` : 'harga: pilih model dari daftar'}</span>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="label" htmlFor={`m-${slot}`}>Model utama</label>
                    <input id={`m-${slot}`} list={`dl-${slot}`} className="input font-mono text-sm" value={v.model} onChange={(e) => setSlots({ ...slots, [slot]: { ...v, model: e.target.value } })} />
                  </div>
                  <div>
                    <label className="label" htmlFor={`f-${slot}`}>Cadangan</label>
                    <input id={`f-${slot}`} list={`dl-${slot}`} className="input font-mono text-sm" value={v.fallback} placeholder="(tidak ada)" onChange={(e) => setSlots({ ...slots, [slot]: { ...v, fallback: e.target.value } })} />
                  </div>
                </div>
                <datalist id={`dl-${slot}`}>{(models[slot] || []).map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</datalist>
                <button className="mt-1 text-xs font-semibold text-primary hover:underline" onClick={() => setSlots({ ...slots, [slot]: d.slot_defaults[slot] })}>Kembalikan ke bawaan</button>
              </div>
            )
          })}
        </div>
        <button className="btn btn-primary mt-4" disabled={busy === 'slots'} onClick={() => run('slots', () => put({ slots }), 'Model disimpan')}>{busy === 'slots' && <Spinner />} Validasi & simpan model</button>
      </Section>

      <Section title="Pola nama produk" desc="Dipakai agen saat menyusun nama (10–100 karakter). Bagian dalam kurung siku diisi dari data sumber.">
        <div className="flex gap-2">
          <input aria-label="Pola nama produk" className="input" value={other.pattern} onChange={(e) => setOther({ ...other, pattern: e.target.value })} />
          <button className="btn shrink-0" onClick={() => run('pat', () => put({ name_pattern: other.pattern }), 'Pola disimpan')}>Simpan</button>
        </div>
      </Section>

      <Section title="Aturan harga" desc="Harga jual = harga beli di dokumen + aturan ini, dihitung kode. AI tidak menentukan harga. Tanpa aturan atau tanpa harga beli, kolom harga dikosongkan dan wajib diisi manusia. Aturan paling spesifik yang dipakai.">
        <div className="overflow-x-auto rounded-lg border border-line">
          <table className="tbl">
            <thead><tr><th className="th">Cakupan</th><th className="th">Kategori</th><th className="th text-right">Markup</th><th className="th text-right">Pembulatan</th><th className="th text-right">Harga min.</th><th className="th"><span className="sr-only">Aksi</span></th></tr></thead>
            <tbody>
              {(rules.data || []).map((r) => (
                <tr key={r.id}>
                  <td className="td">{SCOPE[r.scope]}</td><td className="td">{r.category_name || '—'}</td>
                  <td className="td text-right num">{r.markup_pct}%</td><td className="td text-right num">{r.rounding ? `kelipatan ${r.rounding}` : '—'}</td><td className="td text-right num">{r.min_price || '—'}</td>
                  <td className="td"><button className="btn btn-sm" aria-label="Hapus aturan" onClick={() => run('rule', () => api(`${C(cid)}/ai/pricing-rules/${r.id}`, { method: 'DELETE' }).then(rules.reload), 'Aturan dihapus')}><Trash2 className="h-3.5 w-3.5" /></button></td>
                </tr>
              ))}
              {rules.data?.length === 0 && <tr><td colSpan={6} className="td text-center text-muted-fg">Belum ada aturan: harga hasil impor akan kosong.</td></tr>}
            </tbody>
          </table>
        </div>
        <form className="mt-4 grid items-end gap-3 sm:grid-cols-3 lg:grid-cols-6" onSubmit={(e) => { e.preventDefault(); run('rule', () => api(`${C(cid)}/ai/pricing-rules`, { method: 'POST', body: { ...rule, markup_pct: Number(rule.markup_pct), rounding: Number(rule.rounding), min_price: Number(rule.min_price) } }).then(rules.reload), 'Aturan ditambahkan') }}>
          <div><label className="label" htmlFor="rs">Cakupan</label><select id="rs" className="input" value={rule.scope} onChange={(e) => setRule({ ...rule, scope: e.target.value })}>{Object.entries(SCOPE).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
          <div className="lg:col-span-2"><label className="label" htmlFor="rc">Nama kategori</label><input id="rc" className="input" disabled={rule.scope === 'semua'} required={rule.scope !== 'semua'} placeholder="persis seperti di pohon kategori" value={rule.category_name} onChange={(e) => setRule({ ...rule, category_name: e.target.value })} /></div>
          <div><label className="label" htmlFor="rm">Markup %</label><input id="rm" type="number" min="0" step="0.5" className="input" value={rule.markup_pct} onChange={(e) => setRule({ ...rule, markup_pct: e.target.value })} /></div>
          <div><label className="label" htmlFor="rr">Pembulatan</label><select id="rr" className="input" value={rule.rounding} onChange={(e) => setRule({ ...rule, rounding: e.target.value })}>{[0, 100, 500, 1000].map((n) => <option key={n} value={n}>{n ? `ke atas, kelipatan ${n}` : 'tanpa'}</option>)}</select></div>
          <div><label className="label" htmlFor="rn">Harga min. (Rp)</label><input id="rn" type="number" min="0" className="input" value={rule.min_price} onChange={(e) => setRule({ ...rule, min_price: e.target.value })} /></div>
          <button className="btn btn-primary sm:col-span-3 lg:col-span-6 lg:justify-self-start"><Plus className="h-4 w-4" /> Tambah aturan</button>
        </form>
      </Section>

      <Section title="Pemakaian bulan ini">
        {usage.data && (
          <>
            <div className="overflow-x-auto rounded-lg border border-line">
              <table className="tbl">
                <thead><tr><th className="th">Slot</th><th className="th">Model</th><th className="th text-right">Panggilan</th><th className="th text-right">Token masuk</th><th className="th text-right">Token keluar</th><th className="th text-right">Biaya</th></tr></thead>
                <tbody>
                  {usage.data.per_model.map((u) => <tr key={u.slot + u.model}><td className="td">{u.slot}</td><td className="td font-mono text-xs">{u.model}</td><td className="td text-right num">{u.panggilan}</td><td className="td text-right num">{u.token_masuk.toLocaleString('id-ID')}</td><td className="td text-right num">{u.token_keluar.toLocaleString('id-ID')}</td><td className="td text-right num">{usd(u.biaya_usd)}</td></tr>)}
                  {usage.data.per_model.length === 0 && <tr><td colSpan={6} className="td text-center text-muted-fg">Belum ada pemakaian bulan ini.</td></tr>}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-sm text-muted-fg">{usage.data.baris_draf_ai} baris Draf AI dibuat sejauh ini.</p>
          </>
        )}
      </Section>
    </>
  )
}
