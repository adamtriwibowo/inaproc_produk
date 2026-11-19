// Klien API tipis. Cookie httpOnly dikirim otomatis (same-origin lewat proxy Vite / FastAPI).
export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === 'string' ? detail : detail?.pesan || 'Terjadi kesalahan')
    this.status = status
    this.detail = detail
  }
}

export async function api(path, { method = 'GET', body, form } = {}) {
  const opt = { method, credentials: 'same-origin', headers: {} }
  if (form) opt.body = form
  else if (body !== undefined) {
    opt.headers['Content-Type'] = 'application/json'
    opt.body = JSON.stringify(body)
  }
  const r = await fetch('/api' + path, opt)
  if (r.status === 401 && !path.startsWith('/auth/login')) {
    window.dispatchEvent(new Event('auth:expired'))
  }
  if (!r.ok) {
    let d = null
    try { d = (await r.json()).detail } catch { /* bukan JSON */ }
    throw new ApiError(r.status, d || r.statusText)
  }
  const ct = r.headers.get('content-type') || ''
  return ct.includes('application/json') ? r.json() : r
}

export const C = (cid) => `/companies/${cid}`

export async function download(path, filename) {
  const r = await fetch(path.startsWith('/api') ? path : '/api' + path, { credentials: 'same-origin' })
  if (!r.ok) throw new ApiError(r.status, 'Gagal mengunduh')
  const blob = await r.blob()
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(a.href), 1000)
}
