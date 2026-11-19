import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Building2, CornerDownLeft, FileText, LogOut, Moon, PackagePlus, Search, Sun, Tags } from 'lucide-react'
import { api, C } from '../api.js'

/** Pencarian global (Ctrl+K): halaman, aksi, batch, dan kategori. Data dimuat saat pertama dibuka. */
export default function CommandPalette({ open, onClose, cid, navItems, companies, dark, onToggleTheme, onLogout, canCreate }) {
  const nav = useNavigate()
  const [q, setQ] = useState('')
  const [idx, setIdx] = useState(0)
  const [batches, setBatches] = useState([])
  const [cats, setCats] = useState([])
  const loaded = useRef(null)
  const inputRef = useRef(null)
  const listRef = useRef(null)

  useEffect(() => {
    if (!open) return
    setQ(''); setIdx(0)
    setTimeout(() => inputRef.current?.focus(), 20)
    if (loaded.current === cid) return
    loaded.current = cid
    api(`${C(cid)}/batches`).then(setBatches).catch(() => setBatches([]))
    api(`${C(cid)}/kelayakan/tree`).then((d) => {
      const flat = []
      d.tree.forEach((n1) => n1.children.forEach((n2) => n2.children.forEach((c) => flat.push({ id: c.id, name: c.name, ok: c.ok, path: `${n1.name} › ${n2.name}` }))))
      setCats(flat)
    }).catch(() => setCats([]))
  }, [open, cid])

  const groups = useMemo(() => {
    const ql = q.trim().toLowerCase()
    const has = (t) => !ql || t.toLowerCase().includes(ql)
    const go = (path) => () => { onClose(); nav(path) }
    const out = []
    const pages = navItems.filter((n) => has(n.label)).map((n) => ({ key: `p${n.to}`, label: n.label, icon: n.icon, run: go(n.to ? `/c/${cid}/${n.to}` : `/c/${cid}`) }))
    if (pages.length) out.push({ title: 'Halaman', items: pages })
    const acts = []
    if (canCreate && has('batch baru buat')) acts.push({ key: 'newbatch', label: 'Buat batch baru', icon: PackagePlus, run: go(`/c/${cid}/batch`) })
    if (has('mode gelap terang tema')) acts.push({ key: 'theme', label: dark ? 'Ganti ke mode terang' : 'Ganti ke mode gelap', icon: dark ? Sun : Moon, run: () => { onToggleTheme(); onClose() } })
    companies.filter((c) => c.id !== cid && has(`ganti perusahaan ${c.name}`)).forEach((c) => acts.push({ key: `c${c.id}`, label: `Ganti perusahaan: ${c.name}`, icon: Building2, run: go(`/c/${c.id}`) }))
    if (has('keluar logout')) acts.push({ key: 'logout', label: 'Keluar', icon: LogOut, run: () => { onClose(); onLogout() } })
    if (acts.length) out.push({ title: 'Aksi', items: acts })
    const bs = batches.filter((b) => has(b.name)).slice(0, 6).map((b) => ({ key: `b${b.id}`, label: b.name, hint: b.status, icon: FileText, run: go(`/c/${cid}/batch/${b.id}`) }))
    if (bs.length) out.push({ title: 'Batch', items: bs })
    if (ql.length >= 2) {
      const cs = cats.filter((c) => has(c.name)).slice(0, 8).map((c) => ({
        key: `k${c.id}`, label: c.name, hint: c.ok ? 'Bisa' : 'Tidak bisa', sub: c.path, icon: Tags,
        run: go(`/c/${cid}/kelayakan?q=${encodeURIComponent(c.name)}`),
      }))
      if (cs.length) out.push({ title: 'Kategori', items: cs })
    }
    return out
  }, [q, batches, cats, navItems, companies, cid, dark, canCreate, nav, onClose, onToggleTheme, onLogout])

  const flat = groups.flatMap((g) => g.items)
  useEffect(() => { setIdx(0) }, [q])
  useEffect(() => { listRef.current?.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: 'nearest' }) }, [idx])

  if (!open) return null
  const onKey = (e) => {
    if (e.key === 'Escape') { e.preventDefault(); onClose() }
    else if (e.key === 'ArrowDown') { e.preventDefault(); setIdx((i) => Math.min(i + 1, flat.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setIdx((i) => Math.max(i - 1, 0)) }
    else if (e.key === 'Enter') { e.preventDefault(); flat[idx]?.run() }
  }
  let n = -1
  return (
    <div className="fixed inset-0 z-[70] flex items-start justify-center bg-black/50 p-4 pt-[12vh] backdrop-blur-[2px]" onMouseDown={onClose}>
      <div role="dialog" aria-modal="true" aria-label="Pencarian cepat" className="card w-full max-w-xl overflow-hidden shadow-2xl" onMouseDown={(e) => e.stopPropagation()} onKeyDown={onKey}>
        <div className="flex items-center gap-3 border-b border-line px-4">
          <Search className="h-5 w-5 shrink-0 text-muted-fg" aria-hidden />
          <input
            ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cari halaman, batch, atau kategori…"
            className="h-14 w-full bg-transparent text-base outline-none focus:outline-none focus-visible:outline-none placeholder:text-muted-fg" aria-label="Cari" role="combobox" aria-expanded="true" aria-controls="cmd-list"
          />
          <kbd className="hidden rounded border border-line px-1.5 py-0.5 text-xs text-muted-fg sm:block">Esc</kbd>
        </div>
        <div id="cmd-list" ref={listRef} role="listbox" className="max-h-[50vh] overflow-y-auto p-2">
          {flat.length === 0 && <p className="px-3 py-10 text-center text-sm text-muted-fg">Tidak ada hasil untuk “{q}”.</p>}
          {groups.map((g) => (
            <div key={g.title} className="mb-1">
              <div className="px-3 py-1.5 text-xs font-semibold text-muted-fg">{g.title}</div>
              {g.items.map((it) => {
                n += 1
                const me = n
                const I = it.icon
                const on = me === idx
                return (
                  <button
                    key={it.key} role="option" aria-selected={on} onMouseMove={() => setIdx(me)} onClick={it.run}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm ${on ? 'bg-primary/10 text-primary' : ''}`}
                  >
                    <I className="h-4 w-4 shrink-0" aria-hidden />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium">{it.label}</span>
                      {it.sub && <span className="block truncate text-xs text-muted-fg">{it.sub}</span>}
                    </span>
                    {it.hint && <span className="shrink-0 text-xs text-muted-fg">{it.hint}</span>}
                    {on && <CornerDownLeft className="h-3.5 w-3.5 shrink-0" aria-hidden />}
                  </button>
                )
              })}
            </div>
          ))}
        </div>
        <div className="flex items-center gap-4 border-t border-line px-4 py-2 text-xs text-muted-fg">
          <span><kbd className="rounded border border-line px-1">↑</kbd> <kbd className="rounded border border-line px-1">↓</kbd> pilih</span>
          <span><kbd className="rounded border border-line px-1">Enter</kbd> buka</span>
        </div>
      </div>
    </div>
  )
}
