import { Navigate, useNavigate } from 'react-router-dom'
import { ArrowRight, Boxes, LogOut, ShieldCheck } from 'lucide-react'
import { useAuth, roleIn, LAST_KEY } from '../auth.jsx'
import { Empty } from '../components/ui.jsx'

/** Wajib memilih perusahaan setelah login. Satu perusahaan langsung terpilih. */
export default function Picker({ auto }) {
  const { me, logout } = useAuth()
  const nav = useNavigate()
  const list = me.companies.filter((c) => c.active || me.user.is_super)

  if (auto && list.length === 1) return <Navigate to={`/c/${list[0].id}`} replace />
  const last = localStorage.getItem(LAST_KEY)
  if (auto && last && list.some((c) => c.id === Number(last)) && list.length > 1) {
    return <Navigate to={`/c/${last}`} replace />
  }

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between bg-side px-6 py-4 text-white">
        <div className="flex items-center gap-2.5 font-bold"><Boxes className="h-5 w-5" aria-hidden /> Unggah Massal</div>
        <div className="flex items-center gap-2">
          {me.user.is_super && <button className="btn btn-sm border-white/20 bg-white/10 text-white hover:bg-white/20" onClick={() => nav('/admin')}><ShieldCheck className="h-4 w-4" /> Super Admin</button>}
          <button className="btn btn-sm border-white/20 bg-white/10 text-white hover:bg-white/20" onClick={logout}><LogOut className="h-4 w-4" /> Keluar</button>
        </div>
      </header>
      <main className="mx-auto max-w-2xl px-6 py-10">
        <h1 className="text-[28px] font-bold tracking-tight">Pilih perusahaan</h1>
        <p className="mb-6 mt-1 text-muted-fg">Semua data, template, dan batch dipisah per perusahaan. Anda bisa berpindah kapan saja dari menu kiri.</p>
        {list.length === 0 && <div className="card"><Empty title="Belum ada akses">Anda belum terdaftar di perusahaan mana pun. Minta Super Admin menambahkan akses.</Empty></div>}
        <ul className="space-y-3">
          {list.map((c) => (
            <li key={c.id}>
              <button className="card group flex w-full items-center gap-4 p-4 text-left transition-[border-color,box-shadow] duration-150 hover:border-primary hover:shadow-md" onClick={() => nav(`/c/${c.id}`)}>
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-side text-lg font-bold text-accent" aria-hidden>{c.name[0]}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-base font-bold">{c.name}</span>
                  <span className="block truncate font-mono text-xs text-muted-fg">{c.institution_id}</span>
                </span>
                <span className="hidden text-sm font-medium text-muted-fg sm:block">{roleIn(me, c.id)?.role_label}</span>
                <ArrowRight className="h-5 w-5 text-muted-fg transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-primary" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      </main>
    </div>
  )
}
