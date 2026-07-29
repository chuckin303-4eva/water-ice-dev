import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import { organizationsApi, type OrgUser } from '../api/organizations'
import { useAuth } from '../auth/AuthContext'

/** Org/user management (Phase 1, item 9; ADR-0012). Creating a teammate
 * sets their password directly and shows it once -- there's no email
 * service to send an invite link through, so the admin shares it
 * themselves rather than this pretending to be an email invite flow.
 */
export function AdminDashboardPage() {
  const { currentUser } = useAuth()
  const [users, setUsers] = useState<OrgUser[]>([])
  const [error, setError] = useState<string | null>(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<'admin' | 'member'>('member')
  const [creating, setCreating] = useState(false)
  const [justCreated, setJustCreated] = useState<{ email: string; password: string } | null>(null)
  const [requireReview, setRequireReview] = useState(false)
  const [savingSettings, setSavingSettings] = useState(false)

  function refresh() {
    organizationsApi
      .listUsers()
      .then(setUsers)
      .catch(() => setError('Could not load users'))
  }

  useEffect(refresh, [])
  useEffect(() => {
    organizationsApi
      .getSettings()
      .then((s) => setRequireReview(s.require_review_for_submissions))
      .catch(() => undefined)
  }, [])

  async function handleToggleRequireReview(checked: boolean) {
    setError(null)
    setSavingSettings(true)
    try {
      const settings = await organizationsApi.updateSettings({ require_review_for_submissions: checked })
      setRequireReview(settings.require_review_for_submissions)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not update settings')
    } finally {
      setSavingSettings(false)
    }
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setCreating(true)
    try {
      await organizationsApi.createUser({ email, password, role })
      setJustCreated({ email, password })
      setEmail('')
      setPassword('')
      setRole('member')
      refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create user')
    } finally {
      setCreating(false)
    }
  }

  async function handleToggleActive(user: OrgUser) {
    setError(null)
    try {
      await organizationsApi.updateUser(user.id, { is_active: !user.is_active })
      refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not update user')
    }
  }

  async function handleRoleChange(user: OrgUser, newRole: 'admin' | 'member') {
    setError(null)
    try {
      await organizationsApi.updateUser(user.id, { role: newRole })
      refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not update user')
    }
  }

  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="mb-4 text-lg font-semibold text-slate-900">Team</h1>

      {error && (
        <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
      )}

      <table className="mb-6 w-full text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-slate-500">
            <th className="py-2">Email</th>
            <th className="py-2">Role</th>
            <th className="py-2">Status</th>
            <th className="py-2">Joined</th>
            <th className="py-2"></th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => {
            const isSelf = user.id === currentUser?.id
            return (
              <tr key={user.id} className="border-b border-slate-100">
                <td className="py-2">
                  {user.email} {isSelf && <span className="text-slate-400">(you)</span>}
                </td>
                <td className="py-2">
                  {isSelf ? (
                    user.role
                  ) : (
                    <select
                      value={user.role}
                      onChange={(e) => handleRoleChange(user, e.target.value as 'admin' | 'member')}
                      className="rounded border border-slate-300 px-1 py-0.5"
                    >
                      <option value="member">member</option>
                      <option value="admin">admin</option>
                    </select>
                  )}
                </td>
                <td className="py-2">{user.is_active ? 'Active' : 'Inactive'}</td>
                <td className="py-2 text-slate-500">
                  {new Date(user.created_at).toLocaleDateString()}
                </td>
                <td className="py-2">
                  {!isSelf && (
                    <button
                      type="button"
                      onClick={() => handleToggleActive(user)}
                      className="text-blue-600 underline"
                    >
                      {user.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <div className="mb-6 rounded border border-slate-200 bg-slate-50 p-3 text-sm">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={requireReview}
            disabled={savingSettings}
            onChange={(e) => handleToggleRequireReview(e.target.checked)}
          />
          Require admin review for teammate submissions
        </label>
        <p className="mt-1 text-xs text-slate-500">
          When on, locations created or edited by anyone other than an admin are queued on the{' '}
          <Link to="/admin/review" className="underline">
            Review
          </Link>{' '}
          page instead of applying immediately. Admins are never queued. Off by default.
        </p>
      </div>

      {justCreated && (
        <div className="mb-4 rounded border border-amber-200 bg-amber-50 p-3 text-sm">
          <p className="font-medium text-amber-900">
            Account created for {justCreated.email}. There's no email service to send an
            invite -- share this password with them directly:
          </p>
          <code className="mt-1 block rounded bg-white px-2 py-1">{justCreated.password}</code>
        </div>
      )}

      <h2 className="mb-2 text-sm font-semibold text-slate-700">Add teammate</h2>
      <form onSubmit={handleCreate} className="flex flex-wrap items-end gap-2">
        <label className="text-sm">
          <span className="mb-1 block text-slate-500">Email</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded border border-slate-300 px-2 py-1"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-slate-500">Temporary password</span>
          <input
            type="text"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded border border-slate-300 px-2 py-1"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-slate-500">Role</span>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as 'admin' | 'member')}
            className="rounded border border-slate-300 px-2 py-1"
          >
            <option value="member">member</option>
            <option value="admin">admin</option>
          </select>
        </label>
        <button
          type="submit"
          disabled={creating}
          className="rounded bg-slate-900 px-3 py-1.5 text-sm text-white disabled:opacity-50"
        >
          {creating ? 'Adding…' : 'Add teammate'}
        </button>
      </form>
    </div>
  )
}
