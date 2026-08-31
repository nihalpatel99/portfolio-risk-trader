import { useMemo } from 'react'
import { makeEmptyHolding } from '../holdings.js'

function formatCurrency(value) {
  return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

export default function HoldingsForm({
  holdings,
  onHoldingsChange,
  riskTolerance,
  onRiskToleranceChange,
  question,
  onQuestionChange,
  onSubmit,
  submitting,
}) {
  const updateRow = (id, field, value) => {
    onHoldingsChange(holdings.map((row) => (row.id === id ? { ...row, [field]: value } : row)))
  }

  const removeRow = (id) => {
    onHoldingsChange(holdings.filter((row) => row.id !== id))
  }

  const addRow = () => {
    onHoldingsChange([...holdings, makeEmptyHolding()])
  }

  const summary = useMemo(() => {
    const parsed = holdings
      .map((row) => ({
        ticker: row.ticker.trim().toUpperCase(),
        quantity: Number(row.quantity),
        price: Number(row.price),
      }))
      .filter((row) => row.ticker && row.quantity > 0 && row.price > 0)

    const totalValue = parsed.reduce((sum, row) => sum + row.quantity * row.price, 0)
    return { parsed, totalValue }
  }, [holdings])

  const canSubmit = summary.parsed.length > 0 && !submitting

  return (
    <form
      className="holdings-form"
      onSubmit={(event) => {
        event.preventDefault()
        if (canSubmit) onSubmit(summary.parsed)
      }}
    >
      <h2>Portfolio holdings</h2>

      <div className="holdings-table">
        <div className="holdings-row holdings-row--header">
          <span>Ticker</span>
          <span>Quantity</span>
          <span>Price (USD)</span>
          <span>Value</span>
          <span />
        </div>

        {holdings.map((row) => {
          const quantity = Number(row.quantity)
          const price = Number(row.price)
          const value = quantity > 0 && price > 0 ? quantity * price : null

          return (
            <div className="holdings-row" key={row.id}>
              <input
                type="text"
                placeholder="AAPL"
                value={row.ticker}
                maxLength={10}
                onChange={(e) => updateRow(row.id, 'ticker', e.target.value)}
              />
              <input
                type="number"
                placeholder="50"
                min="0"
                step="any"
                value={row.quantity}
                onChange={(e) => updateRow(row.id, 'quantity', e.target.value)}
              />
              <input
                type="number"
                placeholder="190.32"
                min="0"
                step="any"
                value={row.price}
                onChange={(e) => updateRow(row.id, 'price', e.target.value)}
              />
              <span className="holdings-row__value">{value ? formatCurrency(value) : '—'}</span>
              <button
                type="button"
                className="icon-button"
                aria-label="Remove holding"
                onClick={() => removeRow(row.id)}
                disabled={holdings.length === 1}
              >
                ×
              </button>
            </div>
          )
        })}
      </div>

      <button type="button" className="secondary-button" onClick={addRow}>
        + Add holding
      </button>

      {summary.parsed.length > 0 && (
        <p className="holdings-total">
          Total portfolio value: <strong>{formatCurrency(summary.totalValue)}</strong>
          {' · '}
          {summary.parsed.length} position{summary.parsed.length === 1 ? '' : 's'}
        </p>
      )}

      <div className="field">
        <label htmlFor="risk-tolerance">Risk tolerance</label>
        <select
          id="risk-tolerance"
          value={riskTolerance}
          onChange={(e) => onRiskToleranceChange(e.target.value)}
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
      </div>

      <div className="field">
        <label htmlFor="question">Anything specific for the Advisor? (optional)</label>
        <textarea
          id="question"
          rows={3}
          placeholder="e.g. Should I trim my Apple position?"
          value={question}
          onChange={(e) => onQuestionChange(e.target.value)}
        />
      </div>

      <button type="submit" className="primary-button" disabled={!canSubmit}>
        {submitting ? 'Running analysis…' : 'Run portfolio analysis'}
      </button>
    </form>
  )
}
