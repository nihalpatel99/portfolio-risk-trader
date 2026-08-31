const AGENT_META = {
  News_Analyst: { label: 'News Analyst', className: 'agent-news', icon: '📰' },
  Risk_Calculator: { label: 'Risk Calculator', className: 'agent-risk', icon: '📊' },
  Advisor: { label: 'Advisor', className: 'agent-advisor', icon: '🧭' },
}

function metaFor(agent) {
  return AGENT_META[agent] || { label: agent, className: 'agent-other', icon: '💬' }
}

export default function ConversationPanel({ turns, submitting, error }) {
  const visibleTurns = turns.filter((turn) => AGENT_META[turn.agent])

  if (error) {
    return (
      <div className="conversation-panel">
        <div className="panel-message panel-message--error">
          <strong>Something went wrong.</strong>
          <p>{error}</p>
        </div>
      </div>
    )
  }

  if (submitting && visibleTurns.length === 0) {
    return (
      <div className="conversation-panel">
        <div className="panel-message">
          <div className="spinner" />
          <p>Running the News Analyst, Risk Calculator, and Advisor agents…</p>
        </div>
      </div>
    )
  }

  if (visibleTurns.length === 0) {
    return (
      <div className="conversation-panel">
        <div className="panel-message panel-message--empty">
          <p>Enter your holdings and run the analysis to see the agents' findings here.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="conversation-panel">
      {visibleTurns.map((turn, index) => {
        const meta = metaFor(turn.agent)
        return (
          <article className={`turn-card ${meta.className}`} key={index}>
            <header className="turn-card__header">
              <span className="turn-card__icon" aria-hidden="true">
                {meta.icon}
              </span>
              <span className="turn-card__agent">{meta.label}</span>
            </header>
            <p className="turn-card__text">{turn.text}</p>
          </article>
        )
      })}
    </div>
  )
}
