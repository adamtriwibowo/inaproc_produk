import { api, C } from '../api.js'
import { useCompany } from '../company.js'
import { Empty, ErrorBox, Loading, PageHeader, useLoad } from '../components/ui.jsx'

export default function Audit() {
  const { cid } = useCompany()
  const { data, error, loading } = useLoad(() => api(`${C(cid)}/audit`), [cid])
  if (loading) return <Loading />
  if (error) return <ErrorBox error={error} />
  return (
    <>
      <PageHeader title="Jejak aktivitas" subtitle="Siapa membuat, mengubah, menyetujui, dan mengekspor apa — khusus perusahaan ini." />
      <div className="card overflow-x-auto">
        <table className="tbl">
          <thead><tr><th className="th">Waktu</th><th className="th">Pengguna</th><th className="th">Aksi</th><th className="th">Detail</th></tr></thead>
          <tbody className="divide-y divide-line">
            {data.map((a) => (
              <tr key={a.id}>
                <td className="td whitespace-nowrap font-mono text-xs">{new Date(a.ts).toLocaleString('id-ID')}</td>
                <td className="td text-xs">{a.user}</td>
                <td className="td font-mono text-xs">{a.action}</td>
                <td className="td text-xs text-muted-fg">{a.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data.length === 0 && <Empty>Belum ada aktivitas.</Empty>}
      </div>
    </>
  )
}
