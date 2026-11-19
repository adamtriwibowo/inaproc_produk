import { Navigate, useNavigate } from 'react-router-dom'
import { Building2, LogOut, ShieldCheck } from 'lucide-react'
import { useAuth, roleIn, LAST_KEY } from '../auth.jsx'
import { Empty } from '../components/ui.jsx'

/** Wajib memilih perusahaan setelah login. Satu perusahaan -> langsung terpilih. */
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
    <div className="mx-auto max-w-2xl p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Pilih perusahaan</h1>
        <div className="flex gap-2">
          {me.user.is_super && <button className="btn btn-sm" onClick={() => nav('/admin')}><ShieldCheck className="h-4 w-4" /> Super Admin</button>}
          <button className="btn btn-sm" onClick={logout}><LogOut className="h-4 w-4" /> Keluar</button>
        </div>
      </div>
      {list.length === 0 && <div className="card"><Empty>Anda belum memiliki akses ke perusahaan mana pun. Hubungi Super Admin.</Empty></div>}
      <ul className="space-y-2">
        {list.map((c) => (
          <li key={c.id}>
            <button className="card flex w-full items-center gap-3 p-4 text-left transition-colors duration-200 hover:border-primary" onClick={() => nav(`/c/${c.id}`)}>
              <Building2 className="h-5 w-5 text-primary" aria-hidden />
              <span className="flex-1">
                <span className="block font-semibold">{c.name}</span>
                <span className="block font-mono text-xs text-muted-fg">{c.institution_id}</span>
              </span>
              <span className="text-xs text-muted-fg">{roleIn(me, c.id)?.role_label}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
