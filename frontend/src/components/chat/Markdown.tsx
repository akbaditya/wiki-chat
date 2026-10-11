import { Children, memo } from 'react'
import type { ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'

const CITE = /\[(\d{1,2}(?:\s*,\s*\d{1,2})*)\]/g

function cite(children: ReactNode): ReactNode {
  return Children.map(children, (child) => {
    if (typeof child !== 'string') return child
    const parts: ReactNode[] = []
    let last = 0
    for (const m of child.matchAll(CITE)) {
      const i = m.index ?? 0
      if (i > last) parts.push(child.slice(last, i))
      parts.push(
        <sup key={i} className="mx-px align-super font-sans text-[0.68em] font-medium opacity-40">
          [{m[1]}]
        </sup>,
      )
      last = i + m[0].length
    }
    if (parts.length === 0) return child
    if (last < child.length) parts.push(child.slice(last))
    return <>{parts}</>
  })
}

function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown
      components={{
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-700 underline">
            {children}
          </a>
        ),
        p: ({ children }) => <p className="mb-3 last:mb-0">{cite(children)}</p>,
        li: ({ children }) => <li>{cite(children)}</li>,
        strong: ({ children }) => <strong className="font-semibold">{cite(children)}</strong>,
        em: ({ children }) => <em>{cite(children)}</em>,
        ul: ({ children }) => <ul className="mb-3 list-disc space-y-1 pl-5">{children}</ul>,
        ol: ({ children }) => <ol className="mb-3 list-decimal space-y-1 pl-5">{children}</ol>,
        h1: ({ children }) => <h3 className="mb-1 mt-3 text-lg font-semibold">{children}</h3>,
        h2: ({ children }) => <h3 className="mb-1 mt-3 text-lg font-semibold">{children}</h3>,
        h3: ({ children }) => <h4 className="mb-1 mt-3 font-semibold">{children}</h4>,
        code: ({ children }) => (
          <code className="rounded-md bg-white/60 px-1 py-0.5 font-sans text-[0.85em]">{children}</code>
        ),
      }}
    >
      {children}
    </ReactMarkdown>
  )
}

export default memo(Markdown)