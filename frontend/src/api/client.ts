import type * as T from './types'

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details: Record<string, unknown> = {},
  ) {
    super(message)
  }

  get fields(): Record<string, string> {
    return (this.details.fields as Record<string, string>) ?? {}
  }

  get issues(): T.ScheduleCheck {
    return {
      errors: (this.details.errors as T.Issue[]) ?? [],
      warnings: (this.details.warnings as T.Issue[]) ?? [],
    }
  }
}

type Query = Record<string, string | number | boolean | string[] | null | undefined>

function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value)) value.forEach((v) => params.append(key, v))
    else params.set(key, String(value))
  }
  const qs = params.toString()
  return `/api${path}${qs ? `?${qs}` : ''}`
}

async function request<R>(method: string, path: string, body?: unknown, query?: Query): Promise<R> {
  let response: Response
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      credentials: 'same-origin',
      headers: {
        Accept: 'application/json',
        'X-Requested-With': 'fetch',
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, 'network_error', 'Network error')
  }
  if (response.status === 204) return undefined as R
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const err = data?.error ?? {}
    throw new ApiError(response.status, err.code ?? 'http_error', err.message ?? response.statusText, err.details)
  }
  return data as R
}

const get = <R>(path: string, query?: Query) => request<R>('GET', path, undefined, query)
const post = <R>(path: string, body: unknown = {}) => request<R>('POST', path, body)
const put = <R>(path: string, body: unknown) => request<R>('PUT', path, body)
const patch = <R>(path: string, body: unknown) => request<R>('PATCH', path, body)
const del = <R = void>(path: string) => request<R>('DELETE', path)

export interface ActivityQuery extends Query {
  state?: T.ActivityState[]
  kind?: T.ActivityKind
  group_id?: number
  q?: string
  date_from?: string
  date_to?: string
  mine?: boolean
  order?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

export const api = {
  config: () => get<T.PublicConfig>('/config'),

  auth: {
    me: () => get<T.Me | null>('/auth/me'),
    login: (email: string, password: string) => post<T.Me>('/auth/login', { email, password }),
    register: (data: { name: string; email: string; password: string; locale: T.Locale }) =>
      post<T.Me>('/auth/register', data),
    logout: () => post<void>('/auth/logout'),
    update: (data: Partial<Pick<T.Me, 'name' | 'locale' | 'phone' | 'bio'>>) => patch<T.Me>('/auth/me', data),
    forgot: (email: string) => post<{ ok: boolean }>('/auth/password/forgot', { email }),
    reset: (token: string, password: string) => post<T.Me>('/auth/password/reset', { token, password }),
    changePassword: (current_password: string, new_password: string) =>
      post<T.Me>('/auth/password/change', { current_password, new_password }),
  },

  activities: {
    list: (query: ActivityQuery) => get<T.Page<T.Activity>>('/activities', query),
    get: (id: number) => get<T.ActivityDetail>(`/activities/${id}`),
    check: (data: T.ActivityInput, excludeId?: number) =>
      request<T.ScheduleCheck>('POST', excludeId ? `/activities/check?exclude_id=${excludeId}` : '/activities/check', data),
    create: (data: T.ActivityInput) => post<T.ActivityDetail>('/activities', data),
    update: (id: number, data: Partial<T.ActivityInput>) => patch<T.ActivityDetail>(`/activities/${id}`, data),
    remove: (id: number) => del(`/activities/${id}`),
    close: (id: number) => post<T.CloseResult>(`/activities/${id}/close`),
    calendarUrl: (id: number) => `/api/activities/${id}/calendar.ics`,
    signUp: (id: number, data: { role: T.SignupRole; review_topic?: string; phone?: string }) =>
      post<T.Signup>(`/activities/${id}/signups`, data),
    invites: (id: number) => get<T.Invite[]>(`/activities/${id}/invites`),
    invite: (id: number, data: { invitee_id: number; source?: T.InviteSource; message?: string }) =>
      post<T.Invite>(`/activities/${id}/invites`, data),
  },

  signups: {
    cancel: (id: number) => del(`/signups/${id}`),
    submitReview: (id: number, review_doc_url: string) => put<T.Signup>(`/signups/${id}/review`, { review_doc_url }),
    rate: (id: number, score: number, comment = '') => put<T.Signup>(`/signups/${id}/rating`, { score, comment }),
    toRate: () => get<T.ReviewToRate[]>('/reviews/to-rate'),
  },

  invites: {
    setStatus: (id: number, status: T.InviteStatus) => post<T.Invite>(`/invites/${id}/status`, { status }),
    mine: () => get<T.Invite[]>('/me/invites'),
  },

  groups: {
    list: (includeArchived = false) => get<T.Group[]>('/groups', { include_archived: includeArchived }),
    get: (id: number) => get<T.GroupDetail>(`/groups/${id}`),
    create: (data: T.GroupInput) => post<T.GroupDetail>('/groups', data),
    update: (id: number, data: Partial<T.GroupInput>) => patch<T.GroupDetail>(`/groups/${id}`, data),
    join: (id: number) => post<T.GroupDetail>(`/groups/${id}/join`),
    leave: (id: number) => post<T.GroupDetail>(`/groups/${id}/leave`),
    transfer: (id: number, user_id: number) => post<T.GroupDetail>(`/groups/${id}/transfer`, { user_id }),
    removeMember: (id: number, userId: number) => del<T.GroupDetail>(`/groups/${id}/members/${userId}`),
  },

  rooms: {
    list: () => get<T.Room[]>('/rooms'),
    availability: (q: { date: string; start_time: string; end_time: string; kind: T.ActivityKind; exclude_activity_id?: number }) =>
      get<T.RoomAvailability[]>('/rooms/availability', q),
    slots: (q: { date_from?: string; date_to?: string; room_id?: number }) => get<T.RoomSlot[]>('/rooms/slots', q),
  },

  users: {
    search: (q: string, limit = 10) => get<T.Ref[]>('/users', { q, limit }),
    profile: (id: number) => get<T.PublicProfile>(`/users/${id}`),
  },

  me: {
    dashboard: () => get<T.MeDashboard>('/me/dashboard'),
    summary: () => get<{ pending_invites: number }>('/me/summary'),
  },

  stats: {
    overview: () => get<T.Overview>('/stats/overview'),
    leaderboards: (days?: number) => get<T.Leaderboards>('/stats/leaderboards', { days }),
  },

  admin: {
    dashboard: (month?: string) => get<T.AdminDashboard>('/admin/dashboard', { month }),
    users: (q = '') => get<T.AdminUser[]>('/admin/users', { q }),
    createUser: (data: { name: string; email?: string | null }) => post<T.AdminUser>('/admin/users', data),
    updateUser: (id: number, data: Partial<Pick<T.AdminUser, 'name' | 'email' | 'role' | 'is_active' | 'participation_tracked'>>) =>
      patch<T.AdminUser>(`/admin/users/${id}`, data),
    passwordLink: (id: number) => post<{ link: string }>(`/admin/users/${id}/password-link`),
    rooms: () => get<T.Room[]>('/admin/rooms'),
    createRoom: (data: Omit<T.Room, 'id'>) => post<T.Room>('/admin/rooms', data),
    updateRoom: (id: number, data: Omit<T.Room, 'id'>) => put<T.Room>(`/admin/rooms/${id}`, data),
    deleteRoom: (id: number) => del(`/admin/rooms/${id}`),
    addSlots: (data: { room_id: number; date: string; start_time: string; end_time: string; repeat_weeks: number }) =>
      post<T.RoomSlot[]>('/admin/room-slots', data),
    deleteSlot: (id: number) => del(`/admin/room-slots/${id}`),
    contributions: () => get<T.Contribution[]>('/admin/contributions'),
    addContribution: (data: { user_id: number; kind: T.ContributionKind; date: string; note: string }) =>
      post<T.Contribution>('/admin/contributions', data),
    deleteContribution: (id: number) => del(`/admin/contributions/${id}`),
    exportUrl: (what: 'activities' | 'signups', from?: string, to?: string) =>
      buildUrl(`/admin/export/${what}.csv`, { date_from: from, date_to: to }),
  },
}
