import { memo, useMemo } from 'react'
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from '@tanstack/react-table'
import { ArrowDownToLine, Copy, Trash2 } from 'lucide-react'

const SHORT = {
  D: 'Nama Produk', E: 'Foto Utama (link .png)', F: 'Foto 2', G: 'Foto 3', H: 'Foto 4', I: 'Foto 5', J: 'URL Video', K: 'Deskripsi',
  L: 'PPN', M: 'PPnBM aktif', N: 'PPnBM jenis', O: 'PPnBM kode', P: 'PPnBM bayar', Q: 'Kode KBKI', R: 'PDN: Produksi',
  S: 'PDN: Tenaga kerja', T: 'PDN: Bahan baku', V: 'Negara asal (ISO-3)', W: 'Kuantitas desimal', X: 'Stok', Y: 'Satuan', Z: 'Min. beli',
  AA: 'Pre Order', AB: 'PO (hari)', AC: 'Harga nett (Rp)', AD: 'Berat (gram)', AE: 'Panjang (cm)', AF: 'Lebar (cm)', AG: 'Tinggi (cm)', AH: 'Opsi kirim',
}
const WIDTH = { D: 280, E: 220, F: 160, G: 160, H: 160, I: 160, J: 160, K: 260, Q: 170, R: 230, S: 260, T: 230, V: 90, L: 80, M: 110, X: 80, Z: 80, AA: 110, AB: 80, AC: 130, AD: 100, AE: 90, AF: 90, AG: 90, Y: 100, AH: 110 }
const colWidth = (c) => WIDTH[c.letter] || 170
const NUMERIC = new Set(['X', 'Z', 'AB', 'AC', 'AD', 'AE', 'AF', 'AG'])

/** Kolom grid untuk satu jenis (Barang/Jasa): gabungan kolom semua skema; sel nonaktif bila skema baris tidak punya kolom itu. */
export function buildColumns(schemas, jenis) {
  const map = new Map()
  for (const s of schemas.filter((x) => x.jenis === jenis)) {
    for (const c of s.columns) {
      if (c.idx < 4 || ['kosongkan', 'otomatis', 'sistem'].includes(c.req) || c.letter === 'U') continue
      const key = `${c.letter}|${c.label}`
      if (!map.has(key)) map.set(key, { key, letter: c.letter, idx: c.idx, label: SHORT[c.letter] || c.label, full: c.label, req: c.req, group: c.group, schemaIds: new Set() })
      map.get(key).schemaIds.add(s.id)
      if (c.req === 'wajib') map.get(key).req = 'wajib'
    }
  }
  return [...map.values()].sort((a, b) => a.idx - b.idx)
}

export function optionsFor(schema, col) {
  if (!schema) return null
  if (col.letter === 'Q') return schema.kbki.map((k) => [k[0], `${k[0]} — ${k[1]}`])
  if (col.letter === 'V') return (schema.negara || []).map((n) => [n, n])
  const c = schema.columns.find((x) => x.letter === col.letter)
  return c?.options ? c.options.map((o) => [o, o]) : null
}

const issueMap = (row) => {
  const m = {}
  for (const i of row.issues || []) {
    const k = i.col
    if (!m[k] || (m[k].level === 'warn' && i.level === 'error')) m[k] = i
  }
  return m
}

const Cell = memo(function Cell({ rowId, col, value, schema, issue, disabled, readOnly, onChange, onKeyDown, onPaste }) {
  const id = `cell-${rowId}-${col.letter}`
  const opts = optionsFor(schema, col)
  const cls = `block w-full border-0 bg-transparent px-2 py-1.5 text-sm outline-none focus:bg-primary/5 ${NUMERIC.has(col.letter) ? 'font-mono' : ''}`
  if (disabled) return <td className="bg-muted/60" style={{ minWidth: colWidth(col) }}><div className="px-2 py-1.5 text-xs text-muted-fg">—</div></td>
  const tone = issue ? (issue.level === 'error' ? 'shadow-[inset_0_0_0_1.5px_rgb(var(--bad))] bg-bad-bg/60' : 'shadow-[inset_0_0_0_1.5px_rgb(var(--warn))] bg-warn-bg/60') : ''
  return (
    <td className={`relative border-b border-r border-line/70 p-0 ${tone}`} style={{ minWidth: colWidth(col) }} title={issue?.msg}>
      {opts && opts.length <= 400 ? (
        <select
          id={id} className={cls} value={value ?? ''} disabled={readOnly} aria-label={col.full} aria-invalid={issue?.level === 'error'}
          onChange={(e) => onChange(rowId, col.letter, e.target.value)} onKeyDown={(e) => onKeyDown(e, rowId, col.letter)}
        >
          <option value="" />
          {value && !opts.some((o) => o[0] === value) && <option value={value}>{value}</option>}
          {opts.map((o) => <option key={o[0]} value={o[0]}>{o[1]}</option>)}
        </select>
      ) : (
        <input
          id={id} className={cls} value={value ?? ''} readOnly={readOnly} aria-label={col.full} aria-invalid={issue?.level === 'error'}
          inputMode={NUMERIC.has(col.letter) ? 'numeric' : undefined} autoComplete="off"
          onChange={(e) => onChange(rowId, col.letter, e.target.value)} onKeyDown={(e) => onKeyDown(e, rowId, col.letter)} onPaste={(e) => onPaste(e, rowId, col.letter)}
        />
      )}
    </td>
  )
}, (a, b) => a.value === b.value && a.issue === b.issue && a.schema === b.schema && a.disabled === b.disabled && a.readOnly === b.readOnly && a.col === b.col)

const Row = memo(function Row({ row, index, cols, schema, schemasOfJenis, readOnly, handlers }) {
  const im = issueMap(row)
  const nErr = (row.issues || []).filter((i) => i.level === 'error').length
  return (
    <tr className="group hover:bg-primary/[0.03]">
      <td className="sticky left-0 z-10 border-b border-r border-line bg-card px-1 text-center">
        <div className="flex items-center justify-center gap-0.5">
          <span className="w-6 font-mono text-xs text-muted-fg">{index + 1}</span>
          {!readOnly && (
            <>
              <button className="rounded p-1 text-muted-fg hover:bg-muted" title="Duplikat baris" aria-label={`Duplikat baris ${index + 1}`} onClick={() => handlers.duplicate(row)}><Copy className="h-3.5 w-3.5" /></button>
              <button className="rounded p-1 text-muted-fg hover:bg-bad-bg hover:text-bad" title="Hapus baris" aria-label={`Hapus baris ${index + 1}`} onClick={() => handlers.remove(row)}><Trash2 className="h-3.5 w-3.5" /></button>
            </>
          )}
          {nErr > 0 && <span className="chip bg-bad-bg text-bad" title={`${nErr} error`}>{nErr}</span>}
        </div>
      </td>
      <td className={`sticky left-[84px] z-10 border-b border-r border-line bg-card p-0 ${im.kategori ? 'shadow-[inset_0_0_0_1.5px_rgb(var(--bad))]' : ''}`} style={{ minWidth: 200 }}>
        <select
          id={`cell-${row.id}-_kat`} className="block w-full bg-transparent px-2 py-1.5 text-sm font-medium outline-none focus:bg-primary/5" disabled={readOnly}
          aria-label="Kategori" value={row.schema_id ?? ''} onChange={(e) => handlers.setSchema(row.id, Number(e.target.value))}
          onKeyDown={(e) => handlers.keyDown(e, row.id, '_kat')}
        >
          {!row.schema_id && <option value="">Pilih kategori…</option>}
          {schemasOfJenis.map((s) => <option key={s.id} value={s.id}>{s.category_name}</option>)}
        </select>
      </td>
      {cols.map((c) => (
        <Cell
          key={c.key} rowId={row.id} col={c} value={row.data[c.letter]} schema={schema}
          issue={im[c.letter]} disabled={!c.schemaIds.has(row.schema_id)} readOnly={readOnly}
          onChange={handlers.edit} onKeyDown={handlers.keyDown} onPaste={handlers.paste}
        />
      ))}
    </tr>
  )
})

export default function Grid({ rows, cols, schemas, schemasOfJenis, readOnly, handlers }) {
  const byId = useMemo(() => Object.fromEntries(schemas.map((s) => [s.id, s])), [schemas])
  const helper = createColumnHelper()
  const columns = useMemo(() => [
    helper.display({ id: 'no', header: '#' }),
    helper.display({ id: '_kat', header: 'Kategori' }),
    ...cols.map((c) => helper.display({ id: c.key, header: c.label, meta: c })),
  // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [cols])
  const table = useReactTable({ data: rows, columns, getCoreRowModel: getCoreRowModel() })

  return (
    <div className="card overflow-auto" style={{ maxHeight: 'calc(100vh - 280px)' }} role="region" aria-label="Grid input produk" tabIndex={0}>
      <table className="border-separate border-spacing-0 text-sm">
        <thead className="sticky top-0 z-20">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((h) => {
                const meta = h.column.columnDef.meta
                const first = h.column.id === 'no'
                const kat = h.column.id === '_kat'
                return (
                  <th
                    key={h.id} scope="col"
                    className={`border-b border-r border-line bg-muted px-2 py-2 text-left text-xs font-semibold text-muted-fg ${first ? 'sticky left-0 z-30 w-[84px]' : ''} ${kat ? 'sticky left-[84px] z-30' : ''}`}
                    style={{ minWidth: first ? 84 : kat ? 200 : colWidth(meta) }} title={meta?.full}
                  >
                    <div className="flex items-center justify-between gap-1">
                      <span>{flexRender(h.column.columnDef.header, h.getContext())}{meta?.req === 'wajib' && <span className="text-bad" aria-label="wajib"> *</span>}</span>
                      {meta && !readOnly && (
                        <button className="rounded p-0.5 hover:bg-card" title="Isi ke bawah dari baris pertama" aria-label={`Isi ke bawah ${meta.label}`} onClick={() => handlers.fillColumn(meta)}>
                          <ArrowDownToLine className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </th>
                )
              })}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((r, i) => (
            <Row key={r.original.id} row={r.original} index={i} cols={cols} schema={byId[r.original.schema_id]}
              schemasOfJenis={schemasOfJenis} readOnly={readOnly} handlers={handlers} />
          ))}
        </tbody>
      </table>
    </div>
  )
}
