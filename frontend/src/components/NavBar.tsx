import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { BulldogMark } from './BulldogMark'
import { useAuth } from '../auth'

const LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export function NavBar() {
  const [open, setOpen] = useState(false)
  const close = () => setOpen(false)
  const { user, logOut } = useAuth()

  return (
    <header className="nav">
      <div className="nav-inner">
        <Link to="/" className="brand" onClick={close}>
          <BulldogMark size={38} className="brand-mark" />
          <span className="brand-text">
            <strong>Campus Customs</strong>
            <em>Officially licensed Yale apparel</em>
          </span>
        </Link>

        <button
          className="nav-toggle"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-label="Toggle navigation"
        >
          <span />
          <span />
          <span />
        </button>

        <nav className={open ? 'nav-links open' : 'nav-links'}>
          {LINKS.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              onClick={close}
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
            >
              {l.label}
            </NavLink>
          ))}
          <span className="nav-divider" aria-hidden="true" />
          {user ? (
            <>
              <span className="nav-who" title={user.email}>
                {user.first_name || user.name}
              </span>
              <button
                className="nav-link nav-signout"
                onClick={() => {
                  logOut()
                  close()
                }}
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" onClick={close} className="nav-link">
                Log in
              </NavLink>
              <NavLink to="/create-account" onClick={close} className="nav-cta">
                Create Account
              </NavLink>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
