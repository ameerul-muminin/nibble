import type { Source } from '../lib/api'

type Props = {
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
}

export function ChatBubble({ role, content, sources = [] }: Props) {
  return (
    <div className={`bubble bubble--${role === 'user' ? 'user' : 'cat'}`}>
      {content}
      {sources.length > 0 && (
        <div className="sources">
          {sources.map((source, index) => (
            <span key={index} className="source-chip">
              {source.filename} · p.{source.page}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
