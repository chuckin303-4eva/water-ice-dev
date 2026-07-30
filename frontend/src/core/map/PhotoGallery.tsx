import { useEffect, useRef, useState } from 'react'
import { ApiError, BASE_URL } from '../api/client'
import { photosApi } from '../api/photos'
import type { Photo, PhotoEntityType } from '../api/types'

interface Props {
  entityType: PhotoEntityType
  entityId: string
}

/** Reusable photo gallery for a location or competitor's detail panel
 * (Phase 2 "Photos"; ADR-0018). Selecting a file uploads it immediately,
 * matching ImportCsvControl's "pick and go" pattern rather than a
 * multi-step form. `caption`/`is_primary` exist end-to-end at the API
 * layer (a photo can be marked primary, sorted first) but have no
 * upload-time UI control yet -- only settable by calling the API
 * directly -- same kind of documented, deliberate gap as other
 * "no unlink/edit affordance in v1 yet" cases in this app.
 */
export function PhotoGallery({ entityType, entityId }: Props) {
  const [photos, setPhotos] = useState<Photo[]>([])
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  function refresh() {
    photosApi
      .list(entityType, entityId)
      .then(setPhotos)
      .catch(() => setError('Could not load photos'))
  }

  useEffect(refresh, [entityType, entityId])

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = '' // allow re-selecting the same file later
    if (!file) return

    setUploading(true)
    setError(null)
    try {
      await photosApi.upload(entityType, entityId, file)
      refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not upload photo')
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete(photoId: string) {
    setError(null)
    try {
      await photosApi.remove(entityType, entityId, photoId)
      refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not delete photo')
    }
  }

  return (
    <div className="mb-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-700">Photos</span>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="text-xs text-blue-600 underline disabled:opacity-50"
        >
          {uploading ? 'Uploading…' : '+ Add photo'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={handleFileChange}
          className="hidden"
        />
      </div>

      {photos.length === 0 && <p className="text-xs text-slate-400">No photos yet.</p>}

      {photos.length > 0 && (
        <div className="grid grid-cols-3 gap-1">
          {photos.map((photo) => (
            <div key={photo.id} className="group relative">
              <img
                src={`${BASE_URL}${photo.file_url}`}
                alt={photo.caption ?? ''}
                className="h-16 w-full rounded border border-slate-200 object-cover"
              />
              {photo.is_primary && (
                <span className="absolute left-0.5 top-0.5 rounded bg-amber-500 px-1 text-[9px] leading-4 text-white">
                  ★
                </span>
              )}
              <button
                type="button"
                onClick={() => handleDelete(photo.id)}
                className="absolute right-0.5 top-0.5 hidden rounded-full bg-black/60 px-1 text-[10px] leading-4 text-white group-hover:block"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  )
}
