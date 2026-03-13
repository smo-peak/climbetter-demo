import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getSession, getReadings, type SessionFull, type Reading } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import { formatDate, formatTime, num, scoreColor, asymmetryColor } from '@/lib/utils'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, Radar, ReferenceArea,
} from 'recharts'
import { ArrowLeft, Award } from 'lucide-react'

export default function SessionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const [data, setData] = useState<SessionFull | null>(null)
  const [readings, setReadings] = useState<Reading[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    Promise.all([getSession(id), getReadings(id, 5)])
      .then(([session, r]) => {
        setData(session)
        setReadings(r)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="text-granit-400 text-center py-20">Chargement...</div>
  if (!data) return <div className="text-danger text-center py-20">Session introuvable</div>

  const { session, stats, sequences } = data

  return (
    <div className="max-w-5xl space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Link to="/sessions" className="mt-1 text-granit-400 hover:text-granit-100">
          <ArrowLeft size={20} />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{session.title ?? 'Seance'}</h1>
          <p className="text-granit-400 text-sm mt-1">
            {formatDate(session.started_at)}
            {session.duration_s != null && ` — ${formatTime(session.duration_s)}`}
            <span className="ml-3 capitalize">{session.type.replace(/_/g, ' ')}</span>
          </p>
          {stats?.is_personal_best && (
            <span className="inline-flex items-center gap-1 mt-2 text-xs text-primary-400 bg-primary-500/15 px-2 py-1 rounded">
              <Award size={14} /> Record personnel
            </span>
          )}
        </div>
      </div>

      {/* Force chart */}
      <ForceChart readings={readings} sequences={sequences} startedAt={session.started_at} />

      {/* Stats grid */}
      {stats && <StatsGrid stats={stats} weightKg={user?.weight_kg != null ? num(user.weight_kg) : null} />}

      {/* Score breakdown radar */}
      {stats?.score_breakdown && <ScoreRadar breakdown={stats.score_breakdown} score={num(stats.performance_score)} />}

      {/* Sequence timeline */}
      {sequences.length > 0 && <SequenceTimeline sequences={sequences} sessionStart={session.started_at} />}

      {/* Notes */}
      <div className="bg-granit-800 rounded-xl border border-granit-700 p-5">
        <h3 className="font-semibold mb-2">Notes</h3>
        <p className="text-sm text-granit-300">{session.notes ?? 'Aucune note'}</p>
      </div>
    </div>
  )
}

function ForceChart({ readings, sequences, startedAt }: { readings: Reading[]; sequences: SessionFull['sequences']; startedAt: string }) {
  if (readings.length === 0) return <div className="text-granit-400 text-sm">Pas de donnees de force</div>

  const start = new Date(startedAt).getTime()

  // Merge left/right readings into time-based data points
  const timeMap = new Map<number, { t: number; left: number; right: number }>()
  for (const r of readings) {
    const t = Math.round((new Date(r.time).getTime() - start) / 100) / 10 // seconds with 1 decimal
    const existing = timeMap.get(t) ?? { t, left: 0, right: 0 }
    if (r.sensor_position === 'left') existing.left = num(r.force_kg)
    else if (r.sensor_position === 'right') existing.right = num(r.force_kg)
    timeMap.set(t, existing)
  }

  const chartData = Array.from(timeMap.values()).sort((a, b) => a.t - b.t)

  // Build sequence reference areas
  const loadSeqs = sequences.filter((s) => s.type === 'load')
  const seqAreas = loadSeqs.map((s) => ({
    x1: Math.round((new Date(s.started_at).getTime() - start) / 100) / 10,
    x2: Math.round((new Date(s.ended_at).getTime() - start) / 100) / 10,
  }))

  return (
    <div className="bg-granit-800 rounded-xl border border-granit-700 p-5">
      <h2 className="font-semibold mb-4">Force / Temps</h2>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
          {seqAreas.map((area, i) => (
            <ReferenceArea key={i} x1={area.x1} x2={area.x2} fill="#22C55E" fillOpacity={0.08} />
          ))}
          <XAxis dataKey="t" stroke="#78716C" fontSize={11} tickFormatter={(v: number) => `${v}s`} />
          <YAxis stroke="#78716C" fontSize={11} unit="kg" />
          <Tooltip
            contentStyle={{ background: '#292524', border: '1px solid #44403C', borderRadius: 8, fontSize: 12 }}
            formatter={(value) => [`${Number(value).toFixed(1)} kg`]}
            labelFormatter={(v) => `${v}s`}
          />
          <Area type="monotone" dataKey="left" stroke="#3B82F6" fill="#3B82F6" fillOpacity={0.1} strokeWidth={1.5} dot={false} />
          <Area type="monotone" dataKey="right" stroke="#F97316" fill="#F97316" fillOpacity={0.1} strokeWidth={1.5} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

function StatsGrid({ stats, weightKg }: { stats: SessionFull['stats']; weightKg: number | null }) {
  if (!stats) return null
  return (
    <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
      <StatCard label="Force max" value={`${num(stats.total_max_force_kg).toFixed(1)} kg`}
        sub={weightKg != null && weightKg > 0
          ? `${(num(stats.total_max_force_kg) / weightKg).toFixed(2)} x poids${stats.left_max_force_kg != null ? ` | G: ${num(stats.left_max_force_kg).toFixed(1)} / D: ${num(stats.right_max_force_kg).toFixed(1)}` : ''}`
          : stats.left_max_force_kg != null ? `G: ${num(stats.left_max_force_kg).toFixed(1)} / D: ${num(stats.right_max_force_kg).toFixed(1)}` : undefined} />
      <StatCard label="Force moyenne" value={`${num(stats.total_avg_force_kg).toFixed(1)} kg`}
        sub={stats.left_avg_force_kg != null ? `G: ${num(stats.left_avg_force_kg).toFixed(1)} / D: ${num(stats.right_avg_force_kg).toFixed(1)}` : undefined} />
      <StatCard label="Temps sous charge" value={formatTime(stats.total_load_time_s)} sub={`Repos: ${formatTime(stats.total_rest_time_s)}`} />
      <StatCard label="Sequences" value={String(stats.num_sequences)} />
      <StatCard label="Asymetrie G/D" value={stats.asymmetry_pct != null ? `${num(stats.asymmetry_pct).toFixed(0)}%` : '--'}
        valueClass={stats.asymmetry_pct != null ? asymmetryColor(num(stats.asymmetry_pct)) : ''} />
      <StatCard label="Score" value={stats.performance_score != null ? String(Math.round(num(stats.performance_score))) : '--'}
        valueClass={stats.performance_score != null ? scoreColor(num(stats.performance_score)) : ''} />
    </div>
  )
}

function StatCard({ label, value, sub, valueClass = '' }: { label: string; value: string; sub?: string; valueClass?: string }) {
  return (
    <div className="bg-granit-800 rounded-xl border border-granit-700 p-4">
      <p className="text-xs text-granit-400 uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-2xl font-bold font-mono ${valueClass}`}>{value}</p>
      {sub && <p className="text-xs text-granit-500 mt-1">{sub}</p>}
    </div>
  )
}

function ScoreRadar({ breakdown, score }: { breakdown: { force: number; endurance: number; stability: number; volume: number }; score: number }) {
  const data = [
    { axis: 'Force', value: Math.min(breakdown.force, 100) },
    { axis: 'Endurance', value: Math.min(breakdown.endurance, 100) },
    { axis: 'Stabilite', value: Math.min(breakdown.stability, 100) },
    { axis: 'Volume', value: Math.min(breakdown.volume, 100) },
  ]

  return (
    <div className="bg-granit-800 rounded-xl border border-granit-700 p-5">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold">Score de performance</h3>
        <span className={`text-3xl font-bold font-mono ${scoreColor(score)}`}>{Math.round(score)}</span>
      </div>
      <ResponsiveContainer width="100%" height={250}>
        <RadarChart data={data}>
          <PolarGrid stroke="#44403C" />
          <PolarAngleAxis dataKey="axis" tick={{ fill: '#A8A29E', fontSize: 12 }} />
          <Radar dataKey="value" stroke="#F97316" fill="#F97316" fillOpacity={0.2} strokeWidth={2} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}

function SequenceTimeline({ sequences }: { sequences: SessionFull['sequences']; sessionStart: string }) {
  // Only show one position (or combined) — pick the one with more data
  const leftSeqs = sequences.filter((s) => s.sensor_position === 'left')
  const rightSeqs = sequences.filter((s) => s.sensor_position === 'right')
  const seqs = leftSeqs.length >= rightSeqs.length ? leftSeqs : rightSeqs

  const totalDuration = seqs.reduce((acc, s) => acc + num(s.duration_s), 0)
  if (totalDuration <= 0) return null

  return (
    <div className="bg-granit-800 rounded-xl border border-granit-700 p-5">
      <h3 className="font-semibold mb-3">Timeline sequences ({seqs[0]?.sensor_position})</h3>
      <div className="flex rounded-lg overflow-hidden h-8">
        {seqs.map((s) => {
          const pct = (num(s.duration_s) / totalDuration) * 100
          const isLoad = s.type === 'load'
          return (
            <div
              key={s.id ?? s.sequence_number}
              className={`relative group ${isLoad ? 'bg-success/30' : 'bg-granit-700'}`}
              style={{ width: `${Math.max(pct, 1)}%` }}
              title={`${s.type} #${s.sequence_number}: ${num(s.duration_s).toFixed(1)}s${isLoad ? ` | moy: ${num(s.avg_force_kg).toFixed(1)}kg | max: ${num(s.max_force_kg).toFixed(1)}kg` : ''}`}
            >
              <div className="absolute inset-0 flex items-center justify-center text-[10px] font-mono text-granit-300 opacity-0 group-hover:opacity-100 transition-opacity">
                {num(s.duration_s).toFixed(0)}s
              </div>
            </div>
          )
        })}
      </div>
      <div className="flex justify-between mt-2 text-xs text-granit-400">
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-success/30" /> Charge</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-granit-700" /> Repos</span>
      </div>
    </div>
  )
}
