import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth'
import { ChatResultsProvider } from './chatResults'
import { NavBar } from './components/NavBar'
import { ChatWidget } from './components/ChatWidget'
import { BulldogMark } from './components/BulldogMark'
import { Home } from './pages/Home'
import { Products } from './pages/Products'
import { ProductDetail } from './pages/ProductDetail'
import { About } from './pages/About'
import { CreateAccount, LogIn } from './pages/Account'
import './App.css'

function Footer() {
  return (
    <footer className="foot">
      <div className="foot-inner">
        <div className="foot-brand">
          <BulldogMark size={34} />
          <div>
            <strong>Campus Customs</strong>
            <span>57 Broadway, New Haven, Connecticut</span>
          </div>
        </div>
        <p className="foot-note">
          Officially licensed Yale apparel. Stock shown is read live from our inventory.
        </p>
      </div>
    </footer>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <ChatResultsProvider>
        <BrowserRouter>
          <Site />
        </BrowserRouter>
      </ChatResultsProvider>
    </AuthProvider>
  )
}

function Site() {
  return (
    <>
      <NavBar />
      <main className="shell">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:productId" element={<ProductDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<LogIn />} />
          <Route path="/create-account" element={<CreateAccount />} />
          <Route
            path="*"
            element={
              <div className="section">
                <div className="notice">That page doesn't exist.</div>
              </div>
            }
          />
        </Routes>
      </main>
      <Footer />
      <ChatWidget />
    </>
  )
}
