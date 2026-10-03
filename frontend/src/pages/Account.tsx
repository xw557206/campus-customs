import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { BulldogMark } from '../components/BulldogMark'

/**
 * Log in and Create Account, both wired to the FastAPI backend.
 *
 * Validation is duplicated on purpose: the browser checks give immediate
 * feedback, and the backend re-checks everything because a client can always
 * be bypassed.
 */
function AccountForm({ mode }: { mode: 'login' | 'create' }) {
  const isLogin = mode === 'login'
  const { logIn, signUp, user, logOut } = useAuth()
  const navigate = useNavigate()

  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')

  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState<string | null>(null)

  if (user) {
    return (
      <section className="auth">
        <div className="auth-card">
          <h1>You're signed in</h1>
          <p className="muted">
            Signed in as <strong>{user.email}</strong>.
          </p>
          <button className="btn btn-primary btn-wide" onClick={() => navigate('/products')}>
            Browse the catalogue
          </button>
          <p className="auth-alt">
            Not you? <button className="link-btn" onClick={logOut}>Log out</button>
          </p>
        </div>
      </section>
    )
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setDone(null)

    if (!isLogin && password !== confirm) {
      setError("Those passwords don't match.")
      return
    }

    setBusy(true)
    try {
      if (isLogin) {
        await logIn(email, password)
        setDone('Signed in. Welcome back.')
      } else {
        await signUp({
          first_name: firstName,
          last_name: lastName,
          email,
          password,
          confirm_password: confirm,
        })
        setDone('Account created. You are now signed in.')
      }
      setTimeout(() => navigate('/products'), 700)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="auth">
      <div className="auth-card">
        <BulldogMark size={44} className="auth-mark" />
        <h1>{isLogin ? 'Welcome back' : 'Create your account'}</h1>
        <p className="muted">
          {isLogin
            ? 'Sign in to pick up where you left off.'
            : 'An account keeps your chat history and makes checkout quicker.'}
        </p>

        {error && <div className="notice notice-error form-msg">{error}</div>}
        {done && <div className="notice notice-ok form-msg">{done}</div>}

        <form onSubmit={submit} noValidate>
          {!isLogin && (
            <div className="row2">
              <label>
                First name
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  autoComplete="given-name"
                  required
                />
              </label>
              <label>
                Last name
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  autoComplete="family-name"
                  required
                />
              </label>
            </div>
          )}

          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@yale.edu"
              autoComplete="email"
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={isLogin ? 'current-password' : 'new-password'}
              required
            />
          </label>

          {!isLogin && (
            <label>
              Confirm password
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                autoComplete="new-password"
                required
              />
            </label>
          )}

          <button className="btn btn-primary btn-wide" type="submit" disabled={busy}>
            {busy ? 'Just a moment…' : isLogin ? 'Log in' : 'Create account'}
          </button>
        </form>

        <p className="auth-alt">
          {isLogin ? (
            <>
              No account yet? <Link to="/create-account">Create one</Link>
            </>
          ) : (
            <>
              Already have one? <Link to="/login">Log in</Link>
            </>
          )}
        </p>
      </div>
    </section>
  )
}

export function LogIn() {
  return <AccountForm mode="login" />
}

export function CreateAccount() {
  return <AccountForm mode="create" />
}
