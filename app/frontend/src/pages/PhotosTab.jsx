import { useRef, useState } from 'react'
import { Download, ImagePlus, Link2, Sparkles, Star, Trash2, UploadCloud } from 'lucide-react'
import { api, C, download } from '../api.js'
import { Chip, ErrorBox, Modal, Spinner, useToast } from '../components/ui.jsx'

const PNG = /^https?:\/\/\S+\.png(\?\S*)?$/i
const DRIVE = /^https?:\/\/(drive|docs)\.google\.com\/\S+$/i

export default function PhotosTab({ cid, bid, batch, rows, photos, editable, onChanged }) {
  const toast = useToast()
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)
  const [crop, setCrop] = useState(false)
  const [drag, setDrag] = useState(false)
  const [banner, setBanner] = useState(null)
  const input = useRef(null)
  const base = `${C(cid)}/batches/${bid}`

  const upload = async (files) => {
    files = [...files]; if (!files.length) return
    setErr(null); setBusy(true)
    const form = new FormData(); files.forEach((f) => form.append('files', f)); form.append('crop', crop ? 'true' : 'false')
    try {
      const r = await api(`${base}/photos`, { method: 'POST', form })
      const unmatched = r.diunggah.filter((x) => !x.cocok_dengan).length
      toast(`${r.diunggah.length} foto diproses (PNG 700×700)${unmatched ? `, ${unmatched} belum cocok dengan produk` : ''}`)
      if (r.gagal.length) setErr({ message: 'Sebagian foto gagal diproses', detail: { detail: r.gagal.map((g) => `${g.file}: ${g.alasan}`) } })
      await onChanged()
    } catch (x) { setErr(x) } finally { setBusy(false) }
  }
  const patch = async (p, body) => {
    setErr(null)
    try { await api(`${base}/photos/${p.id}`, { method: 'PATCH', body }); await onChanged() } catch (x) { setErr(x) }
  }
  const del = async (p) => {
    if (!confirm(`Hapus ${p.filename}?`)) return
    try { await api(`${base}/photos/${p.id}`, { method: 'DELETE' }); await onChanged() } catch (x) { setErr(x) }
  }
  const noPhoto = rows.filter((r) => !r.data.E).length
  const noLink = photos.filter((p) => !p.public_url).length

  return (
    <>
      <ErrorBox error={err} />
      <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
        <Chip tone={noPhoto ? 'warn' : 'ok'}>{noPhoto ? `${noPhoto} produk tanpa foto utama` : 'Semua produk punya foto utama'}</Chip>
        <Chip tone={noLink ? 'warn' : 'ok'}>{noLink ? `${noLink} foto belum punya link publik` : 'Semua foto punya link'}</Chip>
        <span className="ml-auto flex gap-2">
          {editable && <button className="btn btn-sm" onClick={() => setBanner({ title: '', points: '' })}><Sparkles className="h-4 w-4" /> Banner jasa</button>}
          <button className="btn btn-sm" disabled={!photos.length} onClick={() => download(`${base}/photos.zip`, `foto_batch${bid}.zip`)}><Download className="h-4 w-4" /> Unduh semua (zip)</button>
        </span>
      </div>

      <p className="mb-3 rounded-md bg-primary/10 p-2.5 text-sm text-primary">
        Template INAPROC membutuhkan <b>link publik berakhiran .png</b>. Unggah foto di sini (diproses otomatis), unggah hasilnya ke imgur atau Google Drive
        (akses “siapa saja dengan link”), lalu tempel linknya di setiap foto. Gunakan foto asli produk.
      </p>

      {editable && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files) }}
          className={`mb-4 flex flex-col items-center gap-2 rounded-lg border-2 border-dashed p-6 text-center transition-colors duration-200 ${drag ? 'border-primary bg-primary/5' : 'border-line'}`}
        >
          {busy ? <Spinner className="h-6 w-6" /> : <UploadCloud className="h-7 w-7 text-muted-fg" aria-hidden />}
          <p className="text-sm">Seret banyak foto ke sini atau <button className="font-semibold text-primary underline" onClick={() => input.current.click()}>pilih file</button></p>
          <p className="text-xs text-muted-fg">Dicocokkan ke produk lewat nama file (sama dengan isi kolom Foto, atau mirip nama produk). EXIF dikoreksi, 1:1 latar putih, 700×700, PNG &lt; 1 MB.</p>
          <label className="flex items-center gap-1.5 text-xs"><input type="checkbox" checked={crop} onChange={(e) => setCrop(e.target.checked)} /> Crop memenuhi kotak (bukan padding putih)</label>
          <input ref={input} type="file" accept="image/*" multiple hidden onChange={(e) => { upload(e.target.files); e.target.value = '' }} />
        </div>
      )}

      {photos.length === 0 ? (
        <div className="card p-8 text-center text-sm text-muted-fg"><ImagePlus className="mx-auto mb-2 h-6 w-6" aria-hidden />Belum ada foto di batch ini.</div>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {photos.map((p) => {
            const ok = !p.public_url || PNG.test(p.public_url) || DRIVE.test(p.public_url)
            return (
              <li key={p.id} className="card overflow-hidden">
                <img src={`/api${base}/photos/${p.id}/file`} alt={`Pratinjau ${p.filename}`} loading="lazy" width="700" height="700" className="aspect-square w-full bg-muted object-contain" />
                <div className="space-y-2 p-2.5">
                  <div className="flex items-center justify-between gap-1 text-xs">
                    <span className="truncate font-mono" title={p.filename}>{p.filename}</span>
                    <span className="shrink-0 text-muted-fg">{p.width}×{p.height} · {(p.size / 1024).toFixed(0)} KB</span>
                  </div>
                  <select className="input !min-h-[30px] text-xs" aria-label="Produk" disabled={!editable} value={p.row_id ?? ''} onChange={(e) => patch(p, { row_id: Number(e.target.value) || 0 })}>
                    <option value="">— belum dicocokkan —</option>
                    {rows.map((r, i) => <option key={r.id} value={r.id}>{i + 1}. {(r.data.D || '(tanpa nama)').slice(0, 50)}</option>)}
                  </select>
                  <div className="relative">
                    <Link2 className="pointer-events-none absolute left-2 top-2 h-3.5 w-3.5 text-muted-fg" aria-hidden />
                    <input
                      className={`input !min-h-[30px] pl-7 text-xs ${ok ? '' : 'border-bad'}`} placeholder="Link publik .png" aria-label="Link publik foto" disabled={!editable}
                      defaultValue={p.public_url} onBlur={(e) => e.target.value !== p.public_url && patch(p, { public_url: e.target.value })}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <Chip tone={p.public_url ? 'ok' : 'warn'}>{p.public_url ? 'Ada link' : 'Belum ada link'}</Chip>
                    {editable && (
                      <span className="flex gap-1">
                        {p.row_id && <button className="btn btn-sm" title="Jadikan foto utama produk" onClick={() => patch(p, { set_main: true })}><Star className="h-3.5 w-3.5" /> Utama</button>}
                        <button className="btn btn-sm" aria-label={`Hapus ${p.filename}`} onClick={() => del(p)}><Trash2 className="h-3.5 w-3.5" /></button>
                      </span>
                    )}
                  </div>
                </div>
              </li>
            )
          })}
        </ul>
      )}

      {banner && (
        <Modal title="Generator banner jasa (1:1, PNG)" onClose={() => setBanner(null)}>
          <form className="space-y-3" onSubmit={async (e) => {
            e.preventDefault(); setErr(null)
            try {
              await api(`${base}/banner`, { method: 'POST', body: { title: banner.title, points: banner.points.split('\n'), row_id: banner.row_id || null } })
              setBanner(null); toast('Banner dibuat'); await onChanged()
            } catch (x) { setErr(x); setBanner(null) }
          }}>
            <div><label className="label" htmlFor="bt">Nama layanan</label><input id="bt" className="input" required value={banner.title} onChange={(e) => setBanner({ ...banner, title: e.target.value })} /></div>
            <div><label className="label" htmlFor="bp">Poin layanan (satu per baris, maks. 6)</label><textarea id="bp" rows={5} className="input" value={banner.points} onChange={(e) => setBanner({ ...banner, points: e.target.value })} /></div>
            <div><label className="label" htmlFor="br">Tautkan ke produk (opsional)</label>
              <select id="br" className="input" value={banner.row_id || ''} onChange={(e) => setBanner({ ...banner, row_id: Number(e.target.value) })}>
                <option value="">—</option>{rows.map((r, i) => <option key={r.id} value={r.id}>{i + 1}. {(r.data.D || '').slice(0, 50)}</option>)}
              </select>
            </div>
            <p className="text-xs text-muted-fg">Banner memakai nama perusahaan aktif. Hanya untuk produk Jasa; produk Barang memakai foto asli.</p>
            <div className="flex justify-end gap-2"><button type="button" className="btn" onClick={() => setBanner(null)}>Batal</button><button className="btn btn-primary">Buat banner</button></div>
          </form>
        </Modal>
      )}
    </>
  )
}
