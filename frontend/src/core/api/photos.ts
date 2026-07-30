import { api } from './client'
import type { Photo, PhotoEntityType } from './types'

function prefix(entityType: PhotoEntityType): string {
  return entityType === 'location' ? '/locations' : '/competitors'
}

export const photosApi = {
  list: (entityType: PhotoEntityType, entityId: string) =>
    api.get<Photo[]>(`${prefix(entityType)}/${entityId}/photos`),
  upload: (entityType: PhotoEntityType, entityId: string, file: File, caption?: string, isPrimary?: boolean) => {
    const formData = new FormData()
    formData.append('file', file)
    if (caption) formData.append('caption', caption)
    if (isPrimary) formData.append('is_primary', 'true')
    return api.postForm<Photo>(`${prefix(entityType)}/${entityId}/photos`, formData)
  },
  remove: (entityType: PhotoEntityType, entityId: string, photoId: string) =>
    api.delete<void>(`${prefix(entityType)}/${entityId}/photos/${photoId}`),
}
