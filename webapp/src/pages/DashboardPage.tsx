import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getSessions, type Session, type SessionList } from '@/lib/api'
import { formatDate, formatTime, num, scoreBg } from '@/lib/utils'
import { useAuth } from '@/contexts/AuthContext'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { ArrowRight, Flame, Trophy, Calendar, TrendingUp, Dumbbell } from 'lucide-react'

function ratioColor(ratio: number): string {
  if (ratio < 0.3) return 'text-danger'
  if (ratio < 0.5) return 'text-warning'
  if (ratio < 0.8) return 'text-success'
  return 'text-secondary-400'
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [sessions, setSessions] = useState<SessionList | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getSessions(1, 50)
      .then(setSessions)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-granit-400 text-center py-20">Chargement...</div>

  const items = sessions?.items ?? []
  const lastSession = items[0]
  const thisWeek = items.filter((s) => {
    const d = new Date(s.started_at)
    const now = new Date()
    const monday = new Date(now)
    monday.setDate(now.getDate() - ((now.getDay() + 6) % 7))
    monday.setHours(0, 0, 0, 0)
    return d >= monday
  })

  return (
    <div className="space-y-6 max-w-5xl">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card
          icon={<Flame className="text-primary-500" size={20} />}
          label="Derniere seance"
          value={lastSession ? formatDate(lastSession.started_at) : '--'}
          sub={lastSession?.duration_s ? formatTime(lastSession.duration_s) : ''}
        />
        <Card
          icon={<Calendar className="text-secondary-500" size={20} />}
          label="Cette semaine"
          value={`${thisWeek.length} seance${thisWeek.length !== 1 ? 's' : ''}`}
          sub={`${items.length} au total`}
        />
        <Card
          icon={<Trophy className="text-warning" size={20} />}
          label="Total sessions"
          value={String(sessions?.total ?? 0)}
          sub=""
        />
        <Card
          icon={<TrendingUp className="text-success" size={20} />}
          label="Sessions ce mois"
          value={String(
            items.filter((s) => {
              const d = new Date(s.started_at)
              const now = new Date()
              return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear()
            }).length
          )}
          sub=""
        />
      </div>

      {/* Force/weight ratio card */}
      {user?.weight_kg != null && user?.best_max_force_kg != null && num(user.weight_kg) > 0 && (
        <div className="bg-granit-800 rounded-xl border border-granit-700 p-5">
          <div className="flex items-center gap-2 mb-2">
            <Dumbbell className="text-primary-500" size={20} />
            <span className="text-xs text-granit-400 uppercase tracking-wide">Ratio force / poids</span>
          </div>
          <div className="flex items-baseline gap-3">
            <span className={`text-3xl font-bold font-mono ${ratioColor(num(user.best_max_force_kg) / num(user.weight_kg))}`}>
              {(num(user.best_max_force_kg) / num(user.weight_kg)).toFixed(2)}
            </span>
            <span className="text-sm text-granit-400">
              {num(user.best_max_force_kg).toFixed(1)} kg / {num(user.weight_kg).toFixed(1)} kg
            </span>
          </div>
        </div>
      )}

      {/* Mini chart: last 10 sessions */}
      {items.length >= 2 && <RecentChart sessions={items.slice(0, 10).reverse()} />}

      {/* Recent sessions */}
      <div className="bg-granit-800 rounded-xl border border-granit-700 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Seances recentes</h2>
          <Link to="/sessions" className="text-primary-400 text-sm flex items-center gap-1 hover:underline">
            Tout voir <ArrowRight size={14} />
          </Link>
        </div>
        {items.length === 0 ? (
          <p className="text-granit-400 text-sm py-4">Aucune seance enregistree. Lance ta premiere seance depuis l'app mobile !</p>
        ) : (
          <div className="space-y-2">
            {items.slice(0, 5).map((s) => (
              <Link
                key={s.id}
                to={`/sessions/${s.id}`}
                className="flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-granit-700 transition-colors"
              >
                <div>
                  <span className="text-sm font-medium">{s.title ?? 'Seance'}</span>
                  <span className="text-xs text-granit-400 ml-3">{formatDate(s.started_at)}</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  {s.duration_s != null && <span className="text-granit-400 font-mono">{formatTime(s.duration_s)}</span>}
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${scoreBg(0)}`}>{s.status}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function Card({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: string; sub: string }) {
  return (
    <div className="bg-granit-800 rounded-xl border border-granit-700 p-4">
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="text-xs text-granit-400 uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-xl font-bold font-mono">{value}</p>
      {sub && <p className="text-xs text-granit-500 mt-1">{sub}</p>}
    </div>
  )
}

function RecentChart({ sessions }: { sessions: Session[] }) {
  const data = sessions.map((s) => ({
    name: new Date(s.started_at).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' }),
    duration: num(s.duration_s),
  }))

  return (
    <div className="bg-granit-800 rounded-xl border border-granit-700 p-5">
      <h2 className="text-lg font-semibold mb-4">Duree des dernieres seances</h2>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data}>
          <XAxis dataKey="name" stroke="#78716C" fontSize={12} />
          <YAxis stroke="#78716C" fontSize={12} unit="s" />
          <Tooltip
            contentStyle={{ background: '#292524', border: '1px solid #44403C', borderRadius: 8, fontSize: 13 }}
            labelStyle={{ color: '#A8A29E' }}
          />
          <Line type="monotone" dataKey="duration" stroke="#F97316" strokeWidth={2} dot={{ r: 4, fill: '#F97316' }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
