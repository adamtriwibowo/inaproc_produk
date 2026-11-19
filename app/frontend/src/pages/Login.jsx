import { useState } from 'react'
import { Boxes, FileArchive, ListChecks, ShieldCheck } from 'lucide-react'
import { useAuth } from '../auth.jsx'
import { ErrorBox, Spinner } from '../components/ui.jsx'

const POINTS = [
  [ListChecks, 'Cek kategori yang boleh Anda isi sesuai KBLI perusahaan'],
  [ShieldCheck, 'Setiap batch ditinjau Reviewer sebelum zip dibuat'],
  [FileArchive, 'Zip siap unggah, sama dengan template resmi INAPROC'],
]

export default function Login() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setErr(null)
    try { await login(email, password) } catch (x) { setErr(x) } finally { setBusy(false) }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[minmax(0,1fr)_480px]">
      <section className="hidden flex-col justify-between bg-side p-12 text-white lg:flex">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-md bg-white/10"><Boxes className="h-5 w-5" aria-hidden /></span>
          <span className="text-lg font-bold tracking-tight">Unggah Massal</span>
        </div>
        <div className="max-w-xl">
          <h1 className="text-[40px] font-bold leading-[1.1] tracking-tight">Dari daftar produk ke zip siap unggah, tanpa salah kolom.</h1>
          <ul className="mt-8 space-y-4">
            {POINTS.map(([I, t]) => (
              <li key={t} className="flex items-start gap-3 text-[15px] text-white/80">
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-accent text-side"><I className="h-4 w-4" aria-hidden /></span>
                {t}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-sm text-white/50">Aplikasi ini tidak login ke INAPROC dan tidak mengunggah otomatis.</p>
      </section>

      <main className="flex items-center justify-center p-6">
        <form onSubmit={submit} className="w-full max-w-sm space-y-4">
          <div className="flex items-center gap-2 text-primary lg:hidden"><Boxes className="h-6 w-6" aria-hidden /><span className="text-lg font-bold">Unggah Massal</span></div>
          <h2 className="text-2xl font-bold tracking-tight">Masuk</h2>
          <ErrorBox error={err} />
          <div>
            <label className="label" htmlFor="email">Email</label>
            <input id="email" className="input" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <label className="label" htmlFor="pw">Password</label>
            <input id="pw" className="input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <button className="btn btn-primary w-full" disabled={busy}>{busy && <Spinner />} Masuk</button>
          <p className="text-sm text-muted-fg">Belum punya akun? Minta Super Admin mengundang Anda.</p>
        </form>
      </main>
    </div>
  )
}
