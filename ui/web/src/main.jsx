import React, { useState } from 'react'
import { createRoot } from 'react-dom/client'

const API = import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8080'

function App(){
  const [question, setQuestion] = useState('')
  const [flightNo, setFlightNo] = useState('')
  const [date, setDate] = useState('')
  const [response, setResponse] = useState(null)
  const [draft, setDraft] = useState(null)
  const [busy, setBusy] = useState(false)

  const seed = async () => {
    setBusy(true)
    await fetch(`${API}/demo/seed`).then(r=>r.json())
    setBusy(false)
  }

  const ask = async () => {
    setBusy(true)
    const r = await fetch(`${API}/ask`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({question, flight_no: flightNo, date})}).then(r=>r.json())
    setResponse(r)
    
    // Dispatch custom event if LLM message is present
    if (r.llm_message) {
      const event = new CustomEvent('llm-message', { detail: r.llm_message })
      window.dispatchEvent(event)
    }
    
    setBusy(false)
  }

  const draftComms = async () => {
    setBusy(true)
    const r = await fetch(`${API}/draft_comms`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({question:'Draft email and sms', flight_no: flightNo, date})}).then(r=>r.json())
    setDraft(r)
    
    // Dispatch custom event if LLM message is present
    if (r.llm_message) {
      const event = new CustomEvent('llm-message', { detail: r.llm_message })
      window.dispatchEvent(event)
    }
    
    setBusy(false)
  }

  return (
    <div className="min-h-screen p-6">
      <header className="max-w-5xl mx-auto mb-6">
        <h1 className="text-3xl font-bold">FlightOps Copilot</h1>
        <p className="text-slate-600">RAG + Agents + Guardrails + Observability demo</p>
      </header>
      <main className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-4">
        <section className="col-span-2 bg-white rounded-2xl p-4 shadow">
          <div className="flex gap-2 mb-3">
            <input className="border p-2 rounded flex-1" value={question} onChange={e=>setQuestion(e.target.value)} />
            <input className="border p-2 rounded w-28" value={flightNo} onChange={e=>setFlightNo(e.target.value)} />
            <input className="border p-2 rounded w-40" value={date} onChange={e=>setDate(e.target.value)} />
            <button onClick={ask} disabled={busy} className="bg-black text-white px-4 py-2 rounded">{busy?'...':'Ask'}</button>
          </div>
          <pre className="bg-slate-100 p-3 rounded text-sm overflow-auto h-80">{response? JSON.stringify(response,null,2) : 'No response yet.'}</pre>
        </section>
        <aside className="bg-white rounded-2xl p-4 shadow">
          <button onClick={seed} disabled={busy} className="bg-indigo-600 text-white w-full py-2 rounded mb-3">{busy?'Seeding...':'Seed demo data'}</button>
          <button onClick={draftComms} disabled={busy} className="bg-emerald-600 text-white w-full py-2 rounded mb-3">{busy?'Drafting...':'Draft comms'}</button>
          <div>
            <h3 className="font-semibold mb-2">Draft Output</h3>
            <pre className="bg-slate-100 p-3 rounded text-sm overflow-auto h-64">{draft? JSON.stringify(draft,null,2) : 'No draft yet.'}</pre>
          </div>
        </aside>
      </main>
      <footer className="max-w-5xl mx-auto mt-6 text-xs text-slate-500">
        <p>Set <code>VITE_GATEWAY_URL</code> to point the UI to a remote gateway.</p>
      </footer>
    </div>
  )
}

createRoot(document.getElementById('root')).render(<App/>)
