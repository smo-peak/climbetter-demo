import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { formatDate, num } from '@/lib/utils'
import { UserCircle, Mail, Calendar, Shield, Save, Weight, Ruler, Mountain, Hand } from 'lucide-react'

const LEVELS = [
  { value: '4a', label: 'Debutant (< 5a)' },
  { value: '5c', label: 'Intermediaire (5a - 6a)' },
  { value: '6b+', label: 'Avance (6a+ - 7a)' },
  { value: '7b', label: 'Expert (7a+ - 8a)' },
  { value: '8a+', label: 'Elite (8a+)' },
]

export default function ProfilePage() {
  const { user } = useAuth()
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    weight_kg: '',
    height_cm: '',
    climbing_level: '',
    hand_dominance: '',
    climbing_years: '',
  })

  if (!user) return <div className="text-granit-400 text-center py-20">Chargement...</div>

  const startEdit = () => {
    setForm({
      weight_kg: user.weight_kg != null ? String(user.weight_kg) : '',
      height_cm: user.height_cm != null ? String(user.height_cm) : '',
      climbing_level: user.climbing_level ?? '',
      hand_dominance: user.hand_dominance ?? '',
      climbing_years: user.climbing_years != null ? String(user.climbing_years) : '',
    })
    setEditing(true)
  }

  const saveProfile = async () => {
    setSaving(true)
    try {
      const data: Record<string, unknown> = {}
      if (form.weight_kg) data.weight_kg = parseFloat(form.weight_kg)
      if (form.height_cm) data.height_cm = parseInt(form.height_cm)
      if (form.climbing_level) data.climbing_level = form.climbing_level
      if (form.hand_dominance) data.hand_dominance = form.hand_dominance
      if (form.climbing_years) data.climbing_years = parseInt(form.climbing_years)

      const token = localStorage.getItem('kc_token')
      const res = await fetch('https://api.climbetter.com/api/v1/users/me', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(data),
      })
      if (!res.ok) throw new Error(`${res.status}`)
      setEditing(false)
      window.location.reload()
    } catch (e) {
      console.error('Save profile failed:', e)
    } finally {
      setSaving(false)
    }
  }

  const weightKg = user.weight_kg != null ? num(user.weight_kg) : null
  const bestForce = user.best_max_force_kg != null ? num(user.best_max_force_kg) : null
  const ratio = weightKg && bestForce && weightKg > 0 ? bestForce / weightKg : null

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold">Mon profil</h1>

      {/* Profile card */}
      <div className="bg-granit-800 rounded-xl border border-granit-700 p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-primary-500/20 flex items-center justify-center text-primary-400 text-2xl font-bold">
              {user.display_name?.charAt(0) ?? '?'}
            </div>
            <div>
              <h2 className="text-xl font-bold">{user.display_name}</h2>
              <p className="text-sm text-granit-400 capitalize">{user.role.replace(/-/g, ' ')}</p>
            </div>
          </div>
          {!editing && (
            <button onClick={startEdit} className="text-sm text-primary-400 hover:underline">
              Modifier
            </button>
          )}
        </div>

        {editing ? (
          <div className="space-y-4">
            <EditRow label="Poids (kg)" value={form.weight_kg} onChange={(v) => setForm({ ...form, weight_kg: v })} type="number" />
            <EditRow label="Taille (cm)" value={form.height_cm} onChange={(v) => setForm({ ...form, height_cm: v })} type="number" />
            <div className="flex items-center gap-3 py-2 border-b border-granit-700/50">
              <span className="text-granit-400"><Mountain size={16} /></span>
              <span className="text-sm text-granit-400 w-40">Niveau</span>
              <select
                value={form.climbing_level}
                onChange={(e) => setForm({ ...form, climbing_level: e.target.value })}
                className="text-sm font-medium bg-granit-700 border border-granit-600 rounded px-2 py-1"
              >
                <option value="">--</option>
                {LEVELS.map((l) => (
                  <option key={l.value} value={l.value}>{l.label}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-3 py-2 border-b border-granit-700/50">
              <span className="text-granit-400"><Hand size={16} /></span>
              <span className="text-sm text-granit-400 w-40">Main dominante</span>
              <select
                value={form.hand_dominance}
                onChange={(e) => setForm({ ...form, hand_dominance: e.target.value })}
                className="text-sm font-medium bg-granit-700 border border-granit-600 rounded px-2 py-1"
              >
                <option value="">--</option>
                <option value="left">Gauche</option>
                <option value="right">Droite</option>
                <option value="ambi">Ambidextre</option>
              </select>
            </div>
            <EditRow label="Annees d'escalade" value={form.climbing_years} onChange={(v) => setForm({ ...form, climbing_years: v })} type="number" />
            <div className="flex gap-3 pt-2">
              <button
                onClick={saveProfile}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-500 text-sm font-semibold text-stone-900 hover:bg-primary-400 disabled:opacity-50"
              >
                <Save size={14} /> {saving ? 'Sauvegarde...' : 'Sauvegarder'}
              </button>
              <button onClick={() => setEditing(false)} className="px-4 py-2 rounded-lg bg-granit-700 text-sm text-granit-300">
                Annuler
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <ProfileRow icon={<Mail size={16} />} label="Email" value={user.email} />
            <ProfileRow icon={<Shield size={16} />} label="Role" value={user.role} />
            <ProfileRow icon={<Calendar size={16} />} label="Membre depuis" value={formatDate(user.created_at)} />
            <ProfileRow icon={<Calendar size={16} />} label="Derniere connexion" value={formatDate(user.last_login_at)} />
            <ProfileRow icon={<UserCircle size={16} />} label="Sessions totales" value={String(user.total_sessions)} />
            {weightKg != null && <ProfileRow icon={<Weight size={16} />} label="Poids" value={`${weightKg.toFixed(1)} kg`} />}
            {user.height_cm != null && <ProfileRow icon={<Ruler size={16} />} label="Taille" value={`${user.height_cm} cm`} />}
            {user.climbing_level && <ProfileRow icon={<Mountain size={16} />} label="Niveau" value={user.climbing_level} />}
            {user.hand_dominance && <ProfileRow icon={<Hand size={16} />} label="Main dominante" value={user.hand_dominance === 'left' ? 'Gauche' : user.hand_dominance === 'right' ? 'Droite' : 'Ambidextre'} />}
            {bestForce != null && (
              <ProfileRow icon={<UserCircle size={16} />} label="Record force" value={`${bestForce.toFixed(1)} kg${ratio ? ` (${ratio.toFixed(2)} x poids)` : ''}`} />
            )}
          </div>
        )}
      </div>

      {/* Ratio card */}
      {ratio != null && (
        <div className="bg-granit-800 rounded-xl border border-granit-700 p-6">
          <h3 className="font-semibold mb-3">Ratio force / poids</h3>
          <div className="text-center py-4">
            <span className={`text-5xl font-bold font-mono ${ratio < 0.3 ? 'text-danger' : ratio < 0.5 ? 'text-warning' : ratio < 0.8 ? 'text-success' : 'text-secondary-400'}`}>
              {ratio.toFixed(2)}
            </span>
            <p className="text-sm text-granit-400 mt-2">
              {ratio < 0.3 ? 'Debutant' : ratio < 0.5 ? 'Intermediaire' : ratio < 0.8 ? 'Avance' : 'Expert'}
              {' — '}{bestForce!.toFixed(1)} kg / {weightKg!.toFixed(1)} kg
            </p>
          </div>
        </div>
      )}

      {/* Subscription placeholder */}
      <div className="bg-granit-800 rounded-xl border border-granit-700 p-6">
        <h3 className="font-semibold mb-3">Abonnement</h3>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-granit-300">Plan actuel</p>
            <p className="text-lg font-bold text-primary-400">Free</p>
          </div>
          <span className="text-xs text-granit-500 bg-granit-700 px-3 py-1.5 rounded-lg">
            Upgrade bientot disponible
          </span>
        </div>
      </div>
    </div>
  )
}

function ProfileRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-granit-700/50 last:border-0">
      <span className="text-granit-400">{icon}</span>
      <span className="text-sm text-granit-400 w-40">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  )
}

function EditRow({ label, value, onChange, type = 'text' }: { label: string; value: string; onChange: (v: string) => void; type?: string }) {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-granit-700/50">
      <span className="text-sm text-granit-400 w-40">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="text-sm font-medium bg-granit-700 border border-granit-600 rounded px-2 py-1 w-32"
      />
    </div>
  )
}
