import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from './api.js'

export const LAST_KEY = 'inaproc:lastCompany'
const Ctx = createContext(null)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }) {
  const [me, setMe] = useState(undefined) // undefined = memuat, null = belum login

  const refresh = useCallback(async () => {
    try { setMe(await api('/auth/me')) } catch { setMe(null) }
  }, [])

  useEffect(() => {
    refresh()
    const h = () => setMe(null)
    window.addEventListener('auth:expired', h)
    return () => window.removeEventListener('auth:expired', h)
  }, [refresh])

  const login = async (email, password) => {
    const d = await api('/auth/login', { method: 'POST', body: { email, password } })
    setMe({ user: d.user, memberships: d.memberships, companies: d.companies })
  }
  const logout = async () => { await api('/auth/logout', { method: 'POST' }); setMe(null) }

  return <Ctx.Provider value={{ me, login, logout, refresh }}>{children}</Ctx.Provider>
}

/** Peran pengguna di perusahaan tertentu: admin | operator | reviewer */
export function roleIn(me, cid) {
  return me?.memberships?.find((m) => m.company_id === Number(cid)) || null
}
