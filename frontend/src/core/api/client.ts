export const BASE_URL = import.meta.env.VITE_API_BASE_URL

const TOKEN_STORAGE_KEY = 'water_ice_access_token'

// localStorage, not an httpOnly cookie -- simplest option for a
// not-yet-public-facing internal tool. Trades some XSS exposure for not
// needing backend cookie/CORS changes that don't exist yet. Revisit
// before this is exposed outside the team.
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers = new Headers(options.headers)
  // FormData bodies must NOT get an explicit Content-Type -- the browser
  // sets multipart/form-data with the correct boundary itself, which we'd
  // otherwise clobber.
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers })

  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      detail = body.detail ?? detail
    } catch {
      // response wasn't JSON -- fall back to statusText
    }
    throw new ApiError(response.status, detail)
  }

  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

async function getBlob(path: string): Promise<Blob> {
  const token = getToken()
  const headers = new Headers()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  const response = await fetch(`${BASE_URL}${path}`, { headers })
  if (!response.ok) {
    throw new ApiError(response.status, response.statusText)
  }
  return response.blob()
}

/** Triggers a browser file download from an already-fetched blob (e.g.
 * a CSV export response) -- there's no <a href> to point at since the
 * endpoint requires an auth header, so the file has to be fetched first
 * and then "clicked" via a throwaway object URL.
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  postForm: <T>(path: string, formData: FormData) => request<T>(path, { method: 'POST', body: formData }),
  getBlob,
}
