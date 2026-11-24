import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { Activity, ArrowUp, AudioLines, Check, ChevronDown, CircleHelp, Command, Cpu, Database, KeyRound, Moon, Plus, Settings2, Sparkles, Sun, X } from 'lucide-react'
import { PromptBondScene } from '@/components/ui/prompt-bond'
import { api, type ChatMessage, type Health } from '@/lib/api'

const suggestions = ['Explain how API caching works.', 'What happens when an API key fails?', 'Explain Docker in simple terms.']
function newId() { return `s-${crypto.randomUUID()}` }

export default function App() {
  const [session, setSession] = useState(newId)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [health, setHealth] = useState<Health | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [dark, setDark] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [systemPrompt, setSystemPrompt] = useState('')
  const [lastMeta, setLastMeta] = useState<ChatMessage['metadata']>()
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => { api.health().then(setHealth).catch(() => setHealth(null)); const timer = window.setInterval(() => api.health().then(setHealth).catch(() => setHealth(null)), 30000); return () => clearInterval(timer) }, [])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages, busy])

  const send = useCallback(async (text: string) => {
    const content = text.trim()
    if (!content || busy) return
    setBusy(true); setError(''); setInput('')
    setMessages(prev => [...prev, { role: 'user', content }])
    try {
      const result = await api.send(session, content, systemPrompt.trim() || undefined)
      setMessages(prev => [...prev, { role: 'assistant', content: result.reply, metadata: result.metadata }])
      setLastMeta(result.metadata)
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : 'Unable to reach Lyftr AI.'
      setError(message); setMessages(prev => prev.filter((item, i) => !(item.role === 'user' && i === prev.length - 1 && item.content === content)))
    } finally { setBusy(false); textareaRef.current?.focus() }
  }, [busy, session, systemPrompt])

  function submit(e: FormEvent) { e.preventDefault(); void send(input) }
  function keydown(e: KeyboardEvent<HTMLTextAreaElement>) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void send(input) } }
  function reset() { setSession(newId()); setMessages([]); setInput(''); setError(''); setLastMeta(undefined) }

  return <PromptBondScene>
    <main className={`app-shell ${dark ? 'dark' : 'light'}`}>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Lyftr AI home"><span className="brand-mark"><AudioLines size={20}/></span><span>lyftr<span className="brand-ai">.ai</span></span></a>
        <div className="workspace-label"><span className="workspace-divider"/>Workspace <ChevronDown size={13}/><span className="crumb-sep">/</span><span className="crumb-active">AI Chat</span></div>
        <div className="top-actions"><span className="top-model"><span className="tiny-dot"/>{health ? 'API connected' : 'Connecting'}</span><button className="new-session" onClick={reset}><Plus size={15}/> New session</button><button className="icon-button" onClick={() => setDark(!dark)} title="Toggle theme" aria-label="Toggle theme">{dark ? <Sun size={17}/> : <Moon size={17}/>}</button></div>
      </header>
      <section className="hero" id="top">
        <motion.div className="eyebrow" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}><span className="eyebrow-spark"><Sparkles size={12}/></span> YOUR THOUGHTS, IN GOOD COMPANY</motion.div>
        <h1><span>Every prompt.</span><br/><em>A little more alive.</em></h1>
        <p className="hero-subtitle">A thoughtful space for your next big idea.</p>
      </section>
      <div className="workspace">
        <DecorativeSide side="left" session={session} count={messages.length} />
        <motion.section className="chat-panel" initial={{ opacity: 0, y: 18, scale: .985 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ duration: .55, delay: .08 }}>
          <div className="panel-head"><div className="assistant-avatar"><Sparkles size={17}/></div><div className="assistant-titles"><strong>AI Assistant</strong><span><i className="status-dot"/> Here with you</span></div><div className="panel-model"><Cpu size={14}/><span>{health ? 'Ready' : 'Offline'}</span><ChevronDown size={12}/></div><button className="panel-settings" onClick={() => setSettingsOpen(true)} aria-label="Assistant settings"><Settings2 size={17}/></button></div>
          <div className="conversation" aria-live="polite">
            {messages.length === 0 && <div className="empty-state"><div className="empty-spark"><Sparkles size={24}/></div><h2>Your next idea starts here.</h2><p>Ask anything. Your conversation stays in context.</p><div className="suggestions">{suggestions.map((item, i) => <button key={item} className="suggestion" onClick={() => void send(item)}><span className="suggestion-index">0{i+1}</span>{item}<ArrowUp size={14}/></button>)}</div></div>}
            <AnimatePresence initial={false}>{messages.map((message, i) => <motion.div key={`${session}-${i}`} className={`message-row ${message.role}`} initial={{ opacity: 0, y: 9 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .24 }}>
              {message.role === 'assistant' && <div className="message-avatar"><Sparkles size={13}/></div>}
              <div className="message-content"><div className="message-bubble" data-testid={message.role === 'assistant' ? 'assistant-message' : undefined}>{message.content}</div>
                {message.role === 'assistant' && message.metadata && <div className="message-meta"><span data-testid="meta-source" className={`meta-source ${message.metadata.resolution_source === 'LLM_CACHE' ? 'cached' : ''}`}><i/>{message.metadata.resolution_source}</span><span data-testid="meta-model">{message.metadata.model}</span><span data-testid="meta-latency">{message.metadata.latency_ms} ms</span><span data-testid="meta-input-tokens">↑ {message.metadata.input_tokens}</span><span data-testid="meta-output-tokens">↓ {message.metadata.output_tokens}</span><span>{message.metadata.key_id ?? 'cache'}</span><span>fallback {message.metadata.fallback_attempts}</span></div>}
              </div>
            </motion.div>)}</AnimatePresence>
            {busy && <div className="message-row assistant"><div className="message-avatar"><Sparkles size={13}/></div><div className="message-bubble typing"><i/><i/><i/></div></div>}
            {error && <div className="error-banner"><CircleHelp size={15}/><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error"><X size={14}/></button></div>}
            <div ref={bottomRef}/>
          </div>
          <form className="composer" onSubmit={submit}><div className="compose-wrap"><textarea ref={textareaRef} data-testid="chat-input" value={input} onChange={e => setInput(e.target.value)} onKeyDown={keydown} placeholder="Ask Lyftr AI anything..." rows={1} maxLength={4000} aria-label="Message Lyftr AI"/><div className="composer-foot"><span className="composer-hint"><Command size={11}/> Enter to send <span>·</span> Shift + Enter for a new line</span><span className="composer-tools">{input.length > 0 && <span>{input.length}/4000</span>}<button className="attach-button" type="button" title="Prompt settings" onClick={() => setSettingsOpen(true)}><Settings2 size={15}/></button><button data-testid="send-button" className="send-button" type="submit" disabled={busy || !input.trim()} aria-label="Send message"><ArrowUp size={17}/></button></span></div></div></form>
          <div className="panel-foot"><span><Database size={12}/> Saved to this session</span><span>Private by design <span className="foot-spark">✳</span></span></div>
        </motion.section>
        <DecorativeSide side="right" health={health} meta={lastMeta} />
      </div>
      <div className="mobile-status"><Infrastructure health={health} meta={lastMeta}/></div>
      <footer className="page-foot"><span>MADE FOR THE WAY YOU THINK</span><span>LYFTR AI <span>©</span> 2025</span></footer>
      <AnimatePresence>{settingsOpen && <motion.div className="modal-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onMouseDown={e => { if (e.target === e.currentTarget) setSettingsOpen(false) }}><motion.div className="settings-modal" initial={{ opacity: 0, y: 12, scale: .98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 8 }}><div className="modal-head"><div><span className="modal-overline">PERSONALIZE</span><h3>Assistant settings</h3></div><button className="icon-button" onClick={() => setSettingsOpen(false)} aria-label="Close settings"><X size={17}/></button></div><label htmlFor="system-prompt-input">System prompt <span>Optional</span></label><textarea id="system-prompt-input" data-testid="system-prompt-input" value={systemPrompt} onChange={e => setSystemPrompt(e.target.value)} placeholder="Give Lyftr AI a little direction..." rows={5}/><p className="modal-note">This instruction is saved with your current session and included in the conversation context.</p><button className="save-button" onClick={() => setSettingsOpen(false)}><Check size={15}/> Done</button></motion.div></motion.div>}</AnimatePresence>
    </main>
  </PromptBondScene>
}

function Infrastructure({ health, meta }: { health: Health | null; meta: ChatMessage['metadata'] }) {
  return <div className="infra-strip"><span><Cpu size={13}/> {meta?.model || 'LLM model'}</span><span><KeyRound size={13}/> {health ? `${health.keys_configured} keys configured` : 'Keys unavailable'}</span><span><Database size={13}/> Cache {health?.cache_enabled ? 'on' : 'unknown'}</span><span><Activity size={13}/> {meta?.resolution_source || 'Awaiting response'}</span></div>
}
function DecorativeSide({ side, session, count, health, meta }: { side: 'left' | 'right'; session?: string; count?: number; health?: Health | null; meta?: ChatMessage['metadata'] }) {
  const items = side === 'left' ? [
    { icon: <Command/>, label: 'SESSION', value: session?.slice(0, 11) || 'New session', color: 'lavender' },
    { icon: <AudioLines/>, label: 'HISTORY', value: `${count ?? 0} messages`, color: 'pink' },
    { icon: <Sparkles/>, label: 'CONTEXT', value: count ? 'In the flow' : 'Ready to begin', color: 'blue' },
    { icon: <Database/>, label: 'STORAGE', value: 'SQLite · saved', color: 'olive' },
  ] : [
    { icon: <Cpu/>, label: 'MODEL', value: meta?.model || 'Configured model', color: 'blue' },
    { icon: <KeyRound/>, label: 'PROVIDERS', value: health ? `${health.keys_configured} keys configured` : 'Checking connection', color: 'yellow' },
    { icon: <Database/>, label: 'CACHE', value: health?.cache_enabled ? 'LiteLLM enabled' : 'Checking status', color: 'lavender' },
    { icon: <Activity/>, label: 'LAST RESPONSE', value: meta?.resolution_source || 'Awaiting response', color: meta?.resolution_source === 'LLM_CACHE' ? 'pink' : 'olive' },
  ]
  return <aside className={`float-column ${side}`}>{items.map((item, i) => <motion.div key={item.label} className={`float-chip ${item.color} chip-${i}`} initial={{ opacity: 0, x: side === 'left' ? -8 : 8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: .15 + i * .08 }}><span className="chip-icon">{item.icon}</span><span className="chip-copy"><span>{item.label}</span><strong>{item.value}</strong></span></motion.div>)}</aside>
}
