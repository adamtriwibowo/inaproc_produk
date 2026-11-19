import { createContext, useContext } from 'react'

/** Perusahaan aktif + peran pengguna di perusahaan itu. */
export const CompanyContext = createContext(null)
export const useCompany = () => useContext(CompanyContext)
