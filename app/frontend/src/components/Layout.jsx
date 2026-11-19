import { useEffect, useRef, useState } from 'react'
import { NavLink, Navigate, Outlet, useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  Boxes, Building2, Check, ChevronsUpDown, ClipboardList, FileSpreadsheet, History, LayoutDashboard, LogOut, Menu,
  PackagePlus, ShieldCheck, Sparkles, Tags, Users, X,
} from 'lucide-react'
import { useAuth, roleIn, LAST_KEY } from '../auth.jsx'
import { CompanyContext } from '../company.js'

// Menu mengikuti alur kerja: siapkan data → kerjakan batch → kelola tim.
const GROUPS = [
  { title: null, items: [{ to: '', label: 'Ringkasan', icon: LayoutDashboard, end: true }] },
  {
    title: 'Siapkan',
    items: [
      { to: 'kelayakan', label: 'Kelayakan kategori', icon: Tags },
      { to: 'kbli', label: 'KBLI perusahaan', icon: ClipboardList },
      { to: 'rekomendasi', label: 'Rekomendasi', icon: Sparkles },
      { to: 'template', label: 'Template', icon: FileSpreadsheet },
    ],
  },
  { title: 'Kerjakan', items: [{ to: 'batch', label: 'Batch produk', icon: PackagePlus }] },
  {
    title: 'Kelola',
    items: [
      { to: 'anggota', label: 'Anggota', icon: Users, roles: ['admin'] },
      { to: 'audit', label: 'Jejak aktivitas', icon: History, roles: ['admin', 'reviewer'] },
    ],
  },
]

function CompanySwitcher({ me, cid, company, nav, onPick }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  useEffect(() => {
    if (!open) return undefined
    const away = (e) => { if (!ref.current?.contains(e.target)) setOpen(false) }
    const esc = (e) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', away)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', away); document.removeEventListener('keydown', esc) }
  }, [open])
  const many = me.companies.length > 1

  return (
    <div ref={ref} className="relative px-3">
      <button
        className="group flex w-full items-center gap-3 rounded-lg bg-white/[0.07] px-3 py-2.5 text-left outline-offset-2 transition-colors duration-200 hover:bg-white/[0.12]"
        onClick={() => many && setOpen((o) => !o)} aria-haspopup={many ? 'listbox' : undefined} aria-expanded={many ? open : undefined}
        aria-label={many ? `Perusahaan aktif: ${company.name}. Ganti perusahaan` : `Perusahaan aktif: ${company.name}`}
      >
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-accent text-side"><Building2 className="h-5 w-5" aria-hidden /></span>
        <span className="min-w-0 flex-1">
          <span className="line-clamp-2 block text-sm font-semibold leading-tight">{company.name}</span>
          <span className="block truncate font-mono text-[11px] text-white/60">{company.institution_id}</span>
        </span>
        {many && <ChevronsUpDown className="h-4 w-4 shrink-0 text-white/60 group-hover:text-white" aria-hidden />}
      </button>
      {open && (
        <ul role="listbox" aria-label="Pilih perusahaan" className="absolute inset-x-3 top-full z-50 mt-1.5 rounded-lg bg-card p-1 text-fg shadow-xl ring-1 ring-black/10">
          {me.companies.map((c) => {
            const r = roleIn(me, c.id)
            const on = c.id === Number(cid)
            return (
              <li key={c.id}>
                <button
                  role="option" aria-selected={on}
                  className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm transition-colors duration-150 hover:bg-muted"
                  onClick={() => { setOpen(false); onPick(); nav(`/c/${c.id}`) }}
                >
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{c.name}</span>
                    <span className="block text-xs text-muted-fg">{r?.role_label}</span>
                  </span>
                  {on && <Check className="h-4 w-4 text-primary" aria-hidden />}
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

export default function Layout() {
  const { cid } = useParams()
  const { me, logout } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [drawer, setDrawer] = useState(false)
  const m = roleIn(me, cid)
  const company = me.companies.find((c) => c.id === Number(cid))

  useEffect(() => { if (m) localStorage.setItem(LAST_KEY, cid) }, [cid, m])
  useEffect(() => { setDrawer(false) }, [loc.pathname])
  useEffect(() => {
    if (!drawer) return undefined
    const esc = (e) => e.key === 'Escape' && setDrawer(false)
    document.addEventListener('keydown', esc)
    return () => document.removeEventListener('keydown', esc)
  }, [drawer])
  if (!m || !company) return <Navigate to="/pilih" replace />

  const visible = GROUPS
    .map((g) => ({ ...g, items: g.items.filter((n) => !n.roles || n.roles.includes(m.role) || me.user.is_super) }))
    .filter((g) => g.items.length)

  const sidebar = (
    <div className="flex h-full flex-col bg-side text-white">
      <div className="flex items-center gap-2.5 px-5 pb-4 pt-5">
        <span className="flex h-8 w-8 items-center justify-center rounded-md bg-white/10"><Boxes className="h-[18px] w-[18px]" aria-hidden /></span>
        <div className="leading-tight">
          <div className="text-[15px] font-bold tracking-tight">Unggah Massal</div>
          <div className="text-xs text-white/60">Katalog Elektronik INAPROC</div>
        </div>
        <button className="ml-auto rounded-md p-1.5 text-white/70 hover:bg-white/10 lg:hidden" onClick={() => setDrawer(false)} aria-label="Tutup menu"><X className="h-5 w-5" /></button>
      </div>

      <CompanySwitcher me={me} cid={cid} company={company} nav={nav} onPick={() => setDrawer(false)} />

      <nav className="mt-4 flex-1 space-y-4 overflow-y-auto px-3 pb-4" aria-label="Menu utama">
        {visible.map((g, gi) => (
          <div key={gi}>
            {g.title && <div className="mb-1 px-3 text-xs font-semibold text-white/50">{g.title}</div>}
            <ul className="space-y-0.5">
              {g.items.map(({ to, label, icon: I, end }) => (
                <li key={to || 'home'}>
                  <NavLink
                    to={to ? `/c/${cid}/${to}` : `/c/${cid}`} end={end}
                    className={({ isActive }) =>
                      `relative flex items-center gap-3 rounded-md px-3 py-2 text-[14px] font-medium transition-colors duration-150 ${
                        isActive ? 'bg-white/[0.12] text-white' : 'text-white/75 hover:bg-white/[0.07] hover:text-white'}`}
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && <span className="absolute inset-y-1.5 left-0 w-1 rounded-r bg-accent" aria-hidden />}
                        <I className="h-[18px] w-[18px] shrink-0" aria-hidden />
                        {label}
                      </>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-white/10 p-3">
        {me.user.is_super && (
          <NavLink to="/admin" className="mb-2 flex items-center gap-3 rounded-md px-3 py-2 text-[14px] font-medium text-white/75 transition-colors duration-150 hover:bg-white/[0.07] hover:text-white">
            <ShieldCheck className="h-[18px] w-[18px]" aria-hidden /> Super Admin
          </NavLink>
        )}
        <div className="flex items-center gap-2.5 rounded-md px-3 py-2">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/15 text-sm font-bold" aria-hidden>
            {me.user.email[0].toUpperCase()}
          </span>
          <div className="min-w-0 flex-1 leading-tight">
            <div className="truncate text-sm font-medium">{me.user.email}</div>
            <div className="truncate text-xs text-white/60">{m.role_label}</div>
          </div>
          <button className="rounded-md p-2 text-white/70 transition-colors duration-150 hover:bg-white/10 hover:text-white" onClick={logout} aria-label="Keluar" title="Keluar">
            <LogOut className="h-[18px] w-[18px]" />
          </button>
        </div>
      </div>
    </div>
  )

  return (
    <CompanyContext.Provider value={{ cid: Number(cid), company, role: m.role, roleLabel: m.role_label }}>
      <div className="min-h-screen">
        <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 lg:block">{sidebar}</aside>

        {drawer && (
          <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
            <div className="absolute inset-0 bg-black/50" onClick={() => setDrawer(false)} />
            <div className="absolute inset-y-0 left-0 w-72 max-w-[85vw] shadow-2xl">{sidebar}</div>
          </div>
        )}

        <div className="lg:pl-64">
          <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-line bg-bg/95 px-4 py-2.5 backdrop-blur lg:hidden">
            <button className="btn btn-sm" onClick={() => setDrawer(true)} aria-label="Buka menu" aria-expanded={drawer}><Menu className="h-5 w-5" /></button>
            <span className="truncate text-sm font-semibold">{company.name}</span>
          </header>
          <main className="mx-auto max-w-[1600px] p-4 lg:p-6">
            <Outlet />
          </main>
        </div>
      </div>
    </CompanyContext.Provider>
  )
}
