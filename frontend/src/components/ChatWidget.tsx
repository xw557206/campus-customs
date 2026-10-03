import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useMatch } from 'react-router-dom'
import { clearChatHistory, fetchChatHistory, formatPrice, sendChat, type Product } from '../api'
import { useAuth } from '../auth'
import { useChatResults } from '../chatResults'
import { BulldogMark } from './BulldogMark'

interface Turn {
  role: 'user' | 'assistant'
  text: string
  products?: Product[]
  /** Set when the turn is an error, so it can be styled and retried. */
  failed?: boolean
}

/** Starter prompts — shoppers often don't know what the assistant can do. */
const SUGGESTIONS = [
  'What hoodies do you have?',
  'Show me something under $40',
  'What sizes are left in the Yale Dad T Shirt?',
]

/** Context-aware starters when the shopper is on a product page. */
const PRODUCT_SUGGESTIONS = [
  'How much is this?',
  'What colours does this come in?',
  'Do you have this in medium?',
]

const GREETING: Turn = {
  role: 'assistant',
  text: "Hi, I'm the Campus Customs assistant. Ask me about a product, a price, or what sizes are in stock.",
}

/**
 * Floating chat widget.
 *
 * It already talks to POST /api/chat, which currently returns a stub reply.
 * When the PydanticAI agent is added, only the backend route changes — this
 * component keeps working, including the product cards it can render from
 * `products` in the response.
 */
export function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [turns, setTurns] = useState<Turn[]>([GREETING])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const logRef = useRef<HTMLDivElement>(null)
  const { setResults } = useChatResults()
  const navigate = useNavigate()
  const { user, token } = useAuth()
  useLocation() // re-render on navigation so the product match below stays current
  // Which product page the shopper is on, if any — sent so "this" resolves.
  const onProduct = useMatch('/products/:productId')
  const viewingId = onProduct?.params.productId ?? null
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const [lastFailed, setLastFailed] = useState<string | null>(null)

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [turns, open])

  // Signed-in shoppers get their saved conversation back. Guests do not — a
  // guest conversation lives only in this tab.
  useEffect(() => {
    if (!user || !token) {
      setTurns([GREETING])
      setHistoryLoaded(false)
      return
    }
    let cancelled = false
    fetchChatHistory(token)
      .then((h) => {
        if (cancelled) return
        const past: Turn[] = h.turns.map((t) => ({
          role: t.role,
          text: t.content,
          products: t.products,
        }))
        setTurns(past.length ? [GREETING, ...past] : [GREETING])
        setHistoryLoaded(true)
      })
      .catch(() => {
        // History is a nicety; failing to load it must not break the chat.
        if (!cancelled) setHistoryLoaded(true)
      })
    return () => {
      cancelled = true
    }
  }, [user, token])

  async function send(message: string, isRetry = false) {
    if (!message || busy) return

    if (!isRetry) setTurns((t) => [...t, { role: 'user', text: message }])
    else setTurns((t) => t.filter((turn) => !turn.failed))
    setDraft('')
    setLastFailed(null)
    setBusy(true)
    try {
      const data = await sendChat(message, { token, productId: viewingId })
      // Guard against a malformed response: never let a missing or non-array
      // `products` field take the page down.
      const products = Array.isArray(data?.products) ? data.products : []
      const reply =
        typeof data?.reply === 'string' && data.reply.trim()
          ? data.reply
          : "I didn't catch that — could you try asking another way?"

      setTurns((t) => [...t, { role: 'assistant', text: reply, products }])
      // Publish to the page. An empty list is published too, so a search that
      // finds nothing clears the previous results rather than leaving them.
      setResults(message, products)
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err)
      setTurns((t) => [
        ...t,
        {
          role: 'assistant',
          failed: true,
          text: `I couldn't reach the shop just now (${detail}). Your message wasn't lost — you can try again.`,
        },
      ])
      setLastFailed(message)
    } finally {
      setBusy(false)
    }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault()
    void send(draft.trim())
  }

  if (!open) {
    return (
      <button className="chat-fab" onClick={() => setOpen(true)} aria-label="Open chat">
        <BulldogMark size={28} />
        <span>Ask us</span>
      </button>
    )
  }

  return (
    <section className="chat" aria-label="Campus Customs chat">
      <header className="chat-head">
        <BulldogMark size={26} />
        <div>
          <strong>Campus Customs</strong>
          <span>
            {user
              ? historyLoaded
                ? 'Your chat is saved'
                : 'Loading your chat…'
              : 'Here to help'}
          </span>
        </div>
        {user && (
          <button
            className="chat-clear"
            title="Delete your saved chat history"
            onClick={async () => {
              if (!token) return
              try {
                await clearChatHistory(token)
                setTurns([GREETING])
              } catch {
                // Leave the conversation as-is if the delete fails.
              }
            }}
          >
            Clear
          </button>
        )}
        <button onClick={() => setOpen(false)} aria-label="Close chat">
          ×
        </button>
      </header>

      <div className="chat-log" ref={logRef}>
        {turns.length === 1 && !busy && (
          <div className="suggestions">
            <span className="suggest-label">Try asking</span>
            {(viewingId ? PRODUCT_SUGGESTIONS : SUGGESTIONS).map((q) => (
              <button key={q} className="suggest" onClick={() => void send(q)}>
                {q}
              </button>
            ))}
          </div>
        )}

        {turns.map((turn, i) => (
          <div key={i} className="turn">
            <p
              className={`bubble bubble-${turn.role}${turn.failed ? ' bubble-failed' : ''}`}
            >
              {turn.text}
            </p>
            {turn.failed && lastFailed && (
              <button className="chat-retry" onClick={() => void send(lastFailed, true)}>
                Try again
              </button>
            )}
            {turn.products && turn.products.length > 0 && (
              <>
                <div className="chat-cards">
                  {turn.products.map((p) => (
                    <Link
                      key={p.product_id}
                      to={`/products/${p.product_id}`}
                      className="chat-card"
                      onClick={() => setOpen(false)}
                    >
                      <img
                        src={p.image_url}
                        alt={p.name}
                        loading="lazy"
                        onError={(e) => {
                          e.currentTarget.style.visibility = 'hidden'
                        }}
                      />
                      <span className="chat-card-name">{p.name}</span>
                      <span className="chat-card-price">{formatPrice(p.price)}</span>
                    </Link>
                  ))}
                </div>
                <button
                  className="chat-seeall"
                  onClick={() => {
                    setOpen(false)
                    navigate('/products')
                  }}
                >
                  See {turn.products.length}{' '}
                  {turn.products.length === 1 ? 'result' : 'results'} on the page →
                </button>
              </>
            )}
          </div>
        ))}
        {busy && (
          <div className="bubble bubble-assistant typing-wrap">
            <span className="typing">
              <span />
              <span />
              <span />
            </span>
            <span className="typing-text">Checking the catalogue…</span>
          </div>
        )}
      </div>

      <form className="chat-form" onSubmit={submit}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask about a product…"
          aria-label="Message"
        />
        <button type="submit" disabled={busy || !draft.trim()}>
          Send
        </button>
      </form>
    </section>
  )
}
