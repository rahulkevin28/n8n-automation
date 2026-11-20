import { useState } from 'react'
import { ApiError, login, register, setAccessToken } from '../services/api'

export function AuthScreen({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setLoading(true); setError('')
    try { const result = await (mode === 'login' ? login(email, password) : register(email, password)); setAccessToken(result.access_token); onAuthenticated() }
    catch (cause) { setError(cause instanceof ApiError ? cause.message : 'Authentication failed.') }
    finally { setLoading(false) }
  }
  return <main className="auth-screen"><section className="auth-brand-panel"><div className="auth-brand-mark"><span /><span /><span /></div><div className="auth-brand-name">FlowForge <em>AI</em></div><div className="auth-flow-lines"><i /><i /><i /></div><p>Turn ambitious ideas into reliable, observable workflows.</p><small>Build thoughtfully. Automate confidently.</small></section><section className="auth-form-panel"><form className="auth-card" onSubmit={submit}><div className="auth-mobile-brand"><div className="auth-brand-mark"><span /><span /><span /></div><strong>FlowForge <em>AI</em></strong></div><span className="auth-eyebrow">{mode === 'login' ? 'WELCOME BACK' : 'GET STARTED'}</span><h1>{mode === 'login' ? 'Sign in to your workspace' : 'Create your workspace'}</h1><p className="auth-subtitle">{mode === 'login' ? 'Continue building better automations.' : 'Start shaping your first intelligent workflow.'}</p><label htmlFor="auth-email">Email address</label><input id="auth-email" required type="email" placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} /><label htmlFor="auth-password">Password</label><div className="auth-password-wrap"><input id="auth-password" required minLength={8} type={showPassword ? 'text' : 'password'} placeholder="At least 8 characters" value={password} onChange={(e) => setPassword(e.target.value)} /><button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? 'Hide' : 'Show'}</button></div>{error && <p className="auth-error">{error}</p>}<button className="auth-submit" disabled={loading}>{loading && <span className="auth-spinner" />}{loading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}</button><p className="auth-switch">{mode === 'login' ? 'New to FlowForge?' : 'Already have an account?'} <button type="button" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}>{mode === 'login' ? 'Create an account' : 'Sign in'}</button></p></form></section></main>
}
