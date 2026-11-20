import { useState } from 'react'
import { ApiError, login, register, setAccessToken } from '../services/api'

export function AuthScreen({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setLoading(true); setError('')
    try { const result = await (mode === 'login' ? login(email, password) : register(email, password)); setAccessToken(result.access_token); onAuthenticated() }
    catch (cause) { setError(cause instanceof ApiError ? cause.message : 'Authentication failed.') }
    finally { setLoading(false) }
  }
  return <main className="auth-screen"><form className="auth-card" onSubmit={submit}><h1>FlowForge AI</h1><p>{mode === 'login' ? 'Sign in to your workspace.' : 'Create your workspace account.'}</p><input required type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} /><input required minLength={8} type="password" placeholder="Password (8+ characters)" value={password} onChange={(e) => setPassword(e.target.value)} />{error && <p className="auth-error">{error}</p>}<button className="primary-button" disabled={loading}>{loading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Register'}</button><button type="button" className="text-button" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>{mode === 'login' ? 'Create an account' : 'Already have an account? Sign in'}</button></form></main>
}
