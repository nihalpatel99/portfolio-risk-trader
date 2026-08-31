const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function analyzePortfolio({ holdings, riskTolerance, question }) {
  const response = await fetch(`${API_URL}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      holdings: holdings.map((h) => ({
        ticker: h.ticker.toUpperCase(),
        quantity: Number(h.quantity),
        price: Number(h.price),
      })),
      risk_tolerance: riskTolerance,
      question,
    }),
  })

  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    throw new Error(detail?.detail || `Request failed with status ${response.status}`)
  }

  const data = await response.json()
  return data.turns
}
