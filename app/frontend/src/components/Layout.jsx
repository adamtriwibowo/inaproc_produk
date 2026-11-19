import { useCallback, useEffect, useRef, useState } from 'react'
import { NavLink, Navigate, Outlet, useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  Boxes, Building2, Check, ChevronDown, ChevronsLeft, ChevronsRight, ChevronsUpDown, ClipboardList, FileSpreadsheet, History,
  LayoutDashboard, LogOut, Menu, Moon, PackagePlus, Search, ShieldCheck, Sparkles, SlidersHorizontal, Sun, Tags, Users, X,
} from 'lucide-react'
import { useAuth, roleIn, LAST_KEY } from '../auth.jsx'
import { CompanyContext } from '../company.js'
import { useTheme } from '../theme.js'
import CommandPalette from './CommandPalette.jsx'

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
      { to: 'ai', label: 'Pengaturan AI', icon: SlidersHorizontal, roles: ['admin'] },
      { to: 'audit', label: 'Jejak aktivitas', icon: History, roles: ['admin', 'reviewer'] },
    ],
  },
]
const TABS = [
  { to: '', label: 'Ringkasan', icon: LayoutDashboard, end: true },
  { to: 'kelayakan', label: 'Kategori', icon: Tags },
  { to: 'batch', label: 'Batch', icon: PackagePlus },
  { to: 'template', label: 'Template', icon: FileSpreadsheet },
]
const SIDEBAR_KEY = 'inaproc:sidebar'

export function BrandMark({ className = 'h-9 w-9' }) {
  return (
    <span className={`flex shrink-0 items-center justify-center rounded-lg bg-primary text-white ${className}`}>
      <Boxes className="h-1/2 w-1/2" aria-hidden />
    </span>
  )
}

function useOutside(open, setOpen) {
  const ref = useRef(null)
  useEffect(() => {
    if (!open) return undefined
    const away = (e) => { if (!ref.current?.contains(e.target)) setOpen(false) }
    const esc = (e) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', away)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', away); document.removeEventListener('keydown', esc) }
  }, [open, setOpen])
  return ref
}

function CompanySwitcher({ me, cid, company, nav, onPick, collapsed }) {
  const [open, setOpen] = useState(false)
  const ref = useOutside(open, setOpen)
  const many = me.companies.length > 1
  return (
    <div ref={ref} className="relative">
      <button
        className={`group flex w-full items-center gap-3 rounded-lg border border-line bg-card text-left transition-colors duration-150 hover:bg-muted ${collapsed ? 'justify-center p-2' : 'p-2.5'}`}
        onClick={() => many && setOpen((o) => !o)} aria-haspopup={many ? 'listbox' : undefined} aria-expanded={many ? open : undefined}
        aria-label={many ? `Perusahaan aktif: ${company.name}. Ganti perusahaan` : `Perusahaan aktif: ${company.name}`} title={collapsed ? company.name : undefined}
      >
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary"><Building2 className="h-[18px] w-[18px]" aria-hidden /></span>
        {!collapsed && (
          <>
            <span className="min-w-0 flex-1">
              <span className="line-clamp-2 block text-sm font-semibold leading-snug">{company.name}</span>
              <span className="block truncate font-mono text-[11px] text-muted-fg">{company.institution_id}</span>
            </span>
            {many && <ChevronsUpDown className="h-4 w-4 shrink-0 text-muted-fg" aria-hidden />}
          </>
        )}
      </button>
      {open && (
        <ul role="listbox" aria-label="Pilih perusahaan" className={`card absolute z-50 w-72 p-1.5 shadow-xl ${collapsed ? 'left-full top-0 ml-2' : 'inset-x-0 top-full mt-2 w-auto'}`}>
          {me.companies.map((c) => {
            const r = roleIn(me, c.id)
            const on = c.id === Number(cid)
            return (
              <li key={c.id}>
                <button
                  role="option" aria-selected={on}
                  className="flex w-full items-center gap-2 rounded-md px-3 py-2.5 text-left text-sm transition-colors duration-150 hover:bg-muted"
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

function UserMenu({ me, m, onLogout, nav }) {
  const [open, setOpen] = useState(false)
  const ref = useOutside(open, setOpen)
  return (
    <div ref={ref} className="relative">
      <button className="flex items-center gap-2.5 rounded-lg p-1.5 pr-2.5 transition-colors duration-150 hover:bg-muted" onClick={() => setOpen((o) => !o)} aria-haspopup="menu" aria-expanded={open}>
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-bold text-white" aria-hidden>{me.user.email[0].toUpperCase()}</span>
        <span className="hidden text-left leading-tight xl:block">
          <span className="block max-w-[180px] truncate text-sm font-medium">{me.user.email}</span>
          <span className="block text-xs text-muted-fg">{m.role_label}</span>
        </span>
        <ChevronDown className="h-4 w-4 text-muted-fg" aria-hidden />
      </button>
      {open && (
        <div role="menu" className="card absolute right-0 top-full z-50 mt-2 w-64 p-1.5 shadow-xl">
          <div className="px-3 py-2">
            <div className="truncate text-sm font-semibold">{me.user.email}</div>
            <div className="text-xs text-muted-fg">{m.role_label}</div>
          </div>
          <div className="my-1 border-t border-line" />
          <button role="menuitem" className="flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-left text-sm hover:bg-muted" onClick={() => { setOpen(false); nav('/pilih') }}><Building2 className="h-4 w-4" aria-hidden /> Ganti perusahaan</button>
          {me.user.is_super && <button role="menuitem" className="flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-left text-sm hover:bg-muted" onClick={() => { setOpen(false); nav('/admin') }}><ShieldCheck className="h-4 w-4" aria-hidden /> Super Admin</button>}
          <button role="menuitem" className="flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-left text-sm text-bad hover:bg-bad-bg" onClick={onLogout}><LogOut className="h-4 w-4" aria-hidden /> Keluar</button>
        </div>
      )}
    </div>
  )
}

export default function Layout() {
  const { cid } = useParams()
  const { me, logout } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const { dark, toggle } = useTheme()
  const [drawer, setDrawer] = useState(false)
  const [palette, setPalette] = useState(false)
  const [collapsed, setCollapsed] = useState(() => { try { return localStorage.getItem(SIDEBAR_KEY) === '1' } catch { return false } })
  const m = roleIn(me, cid)
  const company = me.companies.find((c) => c.id === Number(cid))

  useEffect(() => { if (m) localStorage.setItem(LAST_KEY, cid) }, [cid, m])
  useEffect(() => { setDrawer(false) }, [loc.pathname])
  useEffect(() => { try { localStorage.setItem(SIDEBAR_KEY, collapsed ? '1' : '0') } catch { /* abaikan */ } }, [collapsed])
  useEffect(() => {
    const k = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setPalette((p) => !p) }
      if (e.key === 'Escape') setDrawer(false)
    }
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [])
  const closePalette = useCallback(() => setPalette(false), [])
  if (!m || !company) return <Navigate to="/pilih" replace />

  const visible = GROUPS
    .map((g) => ({ ...g, items: g.items.filter((n) => !n.roles || n.roles.includes(m.role) || me.user.is_super) }))
    .filter((g) => g.items.length)
  const navItems = visible.flatMap((g) => g.items)
  const href = (to) => (to ? `/c/${cid}/${to}` : `/c/${cid}`)
  const canCreate = m.role === 'admin' || m.role === 'operator' || me.user.is_super

  const navCls = (c) => ({ isActive }) =>
    `relative flex items-center rounded-lg text-sm font-medium transition-colors duration-150 ${c ? 'h-10 justify-center' : 'gap-3 px-3 py-2.5'} ${
      isActive ? 'bg-primary/10 text-primary' : 'text-fg/70 hover:bg-muted hover:text-fg'}`

  const sidebar = (mobile) => {
    const c = collapsed && !mobile
    return (
      <div className="flex h-full flex-col bg-card">
        <div className={`flex items-center gap-3 pb-4 pt-5 ${c ? 'justify-center px-2' : 'px-5'}`}>
          <BrandMark />
          {!c && (
            <div className="leading-tight">
              <div className="text-base font-bold tracking-tight">Unggah Massal</div>
              <div className="text-xs text-muted-fg">Katalog Elektronik INAPROC</div>
            </div>
          )}
          {mobile && <button className="ml-auto rounded-lg p-2 text-muted-fg hover:bg-muted" onClick={() => setDrawer(false)} aria-label="Tutup menu"><X className="h-5 w-5" /></button>}
        </div>

        <div className={c ? 'px-2' : 'px-3'}><CompanySwitcher me={me} cid={cid} company={company} nav={nav} onPick={() => setDrawer(false)} collapsed={c} /></div>

        <nav className={`mt-4 flex-1 space-y-4 overflow-y-auto pb-4 ${c ? 'px-2' : 'px-3'}`} aria-label="Menu utama">
          {visible.map((g, gi) => (
            <div key={gi}>
              {g.title && (c ? <div className="mx-3 mb-2 border-t border-line" /> : <div className="mb-1 px-3 text-xs font-semibold text-muted-fg">{g.title}</div>)}
              <ul className="space-y-0.5">
                {g.items.map(({ to, label, icon: I, end }) => (
                  <li key={to || 'home'}>
                    <NavLink to={href(to)} end={end} className={navCls(c)} title={c ? label : undefined} aria-label={c ? label : undefined}>
                      {({ isActive }) => (
                        <>
                          {isActive && !c && <span className="absolute inset-y-2 left-0 w-1 rounded-r-full bg-primary" aria-hidden />}
                          <I className="h-[18px] w-[18px] shrink-0" aria-hidden />
                          {!c && label}
                        </>
                      )}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        <div className={`border-t border-line ${c ? 'p-2' : 'p-3'}`}>
          {mobile ? (
            <>
              <div className="mb-2 flex items-center gap-3 rounded-lg bg-muted/60 p-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-white" aria-hidden>{me.user.email[0].toUpperCase()}</span>
                <div className="min-w-0 flex-1 leading-tight"><div className="truncate text-sm font-medium">{me.user.email}</div><div className="text-xs text-muted-fg">{m.role_label}</div></div>
              </div>
              {me.user.is_super && <NavLink to="/admin" className={navCls(false)}><ShieldCheck className="h-[18px] w-[18px]" aria-hidden /> Super Admin</NavLink>}
              <button className={`${navCls(false)({ isActive: false })} w-full`} onClick={toggle}>{dark ? <Sun className="h-[18px] w-[18px]" aria-hidden /> : <Moon className="h-[18px] w-[18px]" aria-hidden />} {dark ? 'Mode terang' : 'Mode gelap'}</button>
              <button className={`${navCls(false)({ isActive: false })} w-full text-bad`} onClick={logout}><LogOut className="h-[18px] w-[18px]" aria-hidden /> Keluar</button>
            </>
          ) : (
            <button className={`${navCls(c)({ isActive: false })} w-full`} onClick={() => setCollapsed((x) => !x)} aria-label={collapsed ? 'Perluas sidebar' : 'Ciutkan sidebar'} title={collapsed ? 'Perluas sidebar' : undefined}>
              {collapsed ? <ChevronsRight className="h-[18px] w-[18px]" aria-hidden /> : <><ChevronsLeft className="h-[18px] w-[18px]" aria-hidden /> Ciutkan</>}
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <CompanyContext.Provider value={{ cid: Number(cid), company, role: m.role, roleLabel: m.role_label }}>
      <div className="min-h-screen">
        <aside className={`fixed inset-y-0 left-0 z-40 hidden border-r border-line transition-[width] duration-200 lg:block ${collapsed ? 'w-[72px]' : 'w-72'}`}>{sidebar(false)}</aside>

        {drawer && (
          <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
            <div className="absolute inset-0 bg-black/50 backdrop-blur-[2px]" onClick={() => setDrawer(false)} />
            <div className="absolute inset-y-0 left-0 w-[19rem] max-w-[88vw] shadow-2xl">{sidebar(true)}</div>
          </div>
        )}

        <div className={`transition-[padding] duration-200 ${collapsed ? 'lg:pl-[72px]' : 'lg:pl-72'}`}>
          {/* bar atas desktop */}
          <header className="sticky top-0 z-30 hidden h-16 items-center gap-3 border-b border-line bg-card/80 px-6 backdrop-blur lg:flex">
            <button onClick={() => setPalette(true)} className="flex h-10 w-full max-w-md items-center gap-2.5 rounded-lg border border-line bg-bg px-3 text-sm text-muted-fg transition-colors duration-150 hover:bg-muted" aria-label="Buka pencarian cepat">
              <Search className="h-4 w-4" aria-hidden />
              <span className="flex-1 text-left">Cari halaman, batch, kategori…</span>
              <kbd className="rounded border border-line bg-card px-1.5 py-0.5 text-[11px] font-medium">Ctrl K</kbd>
            </button>
            <div className="ml-auto flex items-center gap-1.5">
              <button className="btn btn-sm !min-h-[40px] !px-2.5" onClick={toggle} aria-label={dark ? 'Ganti ke mode terang' : 'Ganti ke mode gelap'} title={dark ? 'Mode terang' : 'Mode gelap'}>{dark ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}</button>
              <UserMenu me={me} m={m} onLogout={logout} nav={nav} />
            </div>
          </header>
          {/* bar atas mobile */}
          <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-line bg-card/90 px-4 py-3 backdrop-blur lg:hidden">
            <BrandMark className="h-9 w-9" />
            <div className="min-w-0 flex-1 leading-tight">
              <div className="truncate text-[15px] font-semibold">{company.name}</div>
              <div className="text-xs text-muted-fg">{m.role_label}</div>
            </div>
            <button className="btn btn-sm !px-2.5" onClick={() => setPalette(true)} aria-label="Cari"><Search className="h-5 w-5" /></button>
            <button className="btn btn-sm !px-2.5" onClick={() => setDrawer(true)} aria-label="Buka menu" aria-expanded={drawer}><Menu className="h-5 w-5" /></button>
          </header>
          <main className="mx-auto max-w-[1520px] px-4 pb-28 pt-6 sm:px-6 lg:px-8 lg:pb-12 lg:pt-8">
            <Outlet />
          </main>
        </div>

        <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-line bg-card/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden" aria-label="Menu cepat">
          {TABS.map(({ to, label, icon: I, end }) => (
            <NavLink key={to || 'home'} to={href(to)} end={end}
              className={({ isActive }) => `flex min-h-[58px] flex-col items-center justify-center gap-0.5 text-[11px] font-medium transition-colors duration-150 ${isActive ? 'text-primary' : 'text-muted-fg'}`}>
              {({ isActive }) => (
                <>
                  <span className={`flex h-7 w-12 items-center justify-center rounded-full transition-colors duration-150 ${isActive ? 'bg-primary/10' : ''}`}><I className="h-5 w-5" aria-hidden /></span>
                  {label}
                </>
              )}
            </NavLink>
          ))}
          <button className="flex min-h-[58px] flex-col items-center justify-center gap-0.5 text-[11px] font-medium text-muted-fg" onClick={() => setDrawer(true)}>
            <span className="flex h-7 w-12 items-center justify-center"><Menu className="h-5 w-5" aria-hidden /></span>
            Menu
          </button>
        </nav>

        <CommandPalette
          open={palette} onClose={closePalette} cid={Number(cid)} navItems={navItems} companies={me.companies}
          dark={dark} onToggleTheme={toggle} onLogout={logout} canCreate={canCreate}
        />
      </div>
    </CompanyContext.Provider>
  )
}
