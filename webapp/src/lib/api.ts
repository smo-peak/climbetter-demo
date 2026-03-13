import { getToken } from './auth'

const API_BASE = 'https://api.climbetter.com/api/v1'

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })

  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`API ${res.status}: ${body}`)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// ── Types ──

export interface User {
  id: string
  email: string
  display_name: string
  first_name: string | null
  last_name: string | null
  role: string
  climbing_level: string | null
  weight_kg: number | null
  height_cm: number | null
  hand_dominance: string | null
  preferred_unit: string | null
  gender: string | null
  birth_year: number | null
  climbing_years: number | null
  total_sessions: number
  best_max_force_kg: number | null
  profile_complete: boolean
  created_at: string
  last_login_at: string
}

export interface Session {
  id: string
  user_id: string
  type: string
  title: string | null
  status: string
  started_at: string
  ended_at: string | null
  duration_s: number | null
  sensor_count: number
  force_threshold_kg: number
  sample_rate_hz: number
  rating: number | null
  perceived_effort: number | null
  notes: string | null
  tags: string[]
  created_at: string
}

export interface SessionStats {
  session_id: string
  total_duration_s: number
  total_load_time_s: number
  total_rest_time_s: number
  load_rest_ratio: number | null
  num_sequences: number
  left_avg_force_kg: number | null
  left_max_force_kg: number | null
  right_avg_force_kg: number | null
  right_max_force_kg: number | null
  total_avg_force_kg: number
  total_max_force_kg: number
  total_impulse_kgs: number | null
  left_right_ratio: number | null
  asymmetry_pct: number | null
  endurance_index: number | null
  fatigue_rate: number | null
  performance_score: number | null
  score_breakdown: { force: number; endurance: number; stability: number; volume: number } | null
  force_vs_avg_pct: number | null
  force_vs_best_pct: number | null
  is_personal_best: boolean
}

export interface Sequence {
  id: string
  session_id: string
  sensor_position: string
  sequence_number: number
  type: string
  started_at: string
  ended_at: string
  duration_s: number
  avg_force_kg: number | null
  max_force_kg: number | null
  min_force_kg: number | null
}

export interface Reading {
  time: string
  sensor_position: string
  force_kg: number
  rfd_kgs: number | null
  quality: number
}

export interface SessionFull {
  session: Session
  stats: SessionStats | null
  sequences: Sequence[]
}

export interface SessionList {
  items: Session[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

// ── API Functions ──

export function syncUser(): Promise<User> {
  return apiFetch<User>('/auth/sync', { method: 'POST', body: '{}' })
}

export function getSessions(page = 1, pageSize = 20): Promise<SessionList> {
  return apiFetch<SessionList>(`/sessions?page=${page}&page_size=${pageSize}`)
}

export function getSession(id: string): Promise<SessionFull> {
  return apiFetch<SessionFull>(`/sessions/${id}`)
}

export function getReadings(sessionId: string, downsample = 10): Promise<Reading[]> {
  return apiFetch<Reading[]>(`/sessions/${sessionId}/readings?downsample=${downsample}`)
}

export function updateSession(id: string, data: { notes?: string; tags?: string[]; rating?: number }): Promise<Session> {
  return apiFetch<Session>(`/sessions/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function getProfile(): Promise<User> {
  return apiFetch<User>('/auth/sync', { method: 'POST', body: '{}' })
}
