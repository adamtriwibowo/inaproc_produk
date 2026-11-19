import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth.jsx'
import { Loading } from './components/ui.jsx'
import Layout from './components/Layout.jsx'
import Login from './pages/Login.jsx'
import Picker from './pages/Picker.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Kelayakan from './pages/Kelayakan.jsx'
import Kbli from './pages/Kbli.jsx'
import Rekomendasi from './pages/Rekomendasi.jsx'
import Templates from './pages/Templates.jsx'
import Batches from './pages/Batches.jsx'
import BatchEditor from './pages/BatchEditor.jsx'
import Members from './pages/Members.jsx'
import Audit from './pages/Audit.jsx'
import AiSettings from './pages/AiSettings.jsx'
import SuperAdmin from './pages/SuperAdmin.jsx'

export default function App() {
  const { me } = useAuth()
  if (me === undefined) return <Loading text="Memuat aplikasi…" />
  if (me === null) {
    return (
      <Routes>
        <Route path="*" element={<Login />} />
      </Routes>
    )
  }
  return (
    <Routes>
      <Route path="/" element={<Picker auto />} />
      <Route path="/pilih" element={<Picker />} />
      <Route path="/admin" element={<SuperAdmin />} />
      <Route path="/c/:cid" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="kelayakan" element={<Kelayakan />} />
        <Route path="kbli" element={<Kbli />} />
        <Route path="rekomendasi" element={<Rekomendasi />} />
        <Route path="template" element={<Templates />} />
        <Route path="batch" element={<Batches />} />
        <Route path="batch/:bid" element={<BatchEditor />} />
        <Route path="anggota" element={<Members />} />
        <Route path="audit" element={<Audit />} />
        <Route path="ai" element={<AiSettings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
