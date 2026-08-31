import { useState } from 'react'
import HoldingsForm from './components/HoldingsForm.jsx'
import ConversationPanel from './components/ConversationPanel.jsx'
import { analyzePortfolio } from './api.js'
import { makeEmptyHolding } from './holdings.js'

export default function App() {
  const [holdings, setHoldings] = useState([makeEmptyHolding()])
  const [riskTolerance, setRiskTolerance] = useState('medium')
  const [question, setQuestion] = useState('')
  const [turns, setTurns] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (parsedHoldings) => {
    setSubmitting(true)
    setError(null)
    setTurns([])

    try {
      const result = await analyzePortfolio({
        holdings: parsedHoldings,
        riskTolerance,
        question: question.trim() || 'Give me a general risk assessment and recommendation for this portfolio.',
      })
      setTurns(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Portfolio Risk &amp; Trading Monitor</h1>
        <p>News Analyst, Risk Calculator, and Advisor agents review your holdings in sequence.</p>
      </header>

      <main className="app-main">
        <HoldingsForm
          holdings={holdings}
          onHoldingsChange={setHoldings}
          riskTolerance={riskTolerance}
          onRiskToleranceChange={setRiskTolerance}
          question={question}
          onQuestionChange={setQuestion}
          onSubmit={handleSubmit}
          submitting={submitting}
        />

        <ConversationPanel turns={turns} submitting={submitting} error={error} />
      </main>

      <footer className="app-footer">
        Educational analysis only — not licensed financial advice.
      </footer>
    </div>
  )
}
