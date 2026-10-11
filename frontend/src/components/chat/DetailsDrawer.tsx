import { useEffect } from 'react'
import type { ReactNode } from 'react'
import type { Details } from '../../types'

const STRATEGY_LABEL: Record<string, string> = {
  none: 'Searched as written',
  rewrite: 'Rewrote the question',
  multi_query: 'Multiple search queries',
  decompose: 'Split into sub-questions',
  expand: 'Expanded with related terms',
}

const fmt = (n: number | undefined) => (typeof n === 'number' ? n.toFixed(3) : '–')

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mb-5">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">{title}</h3>
      {children}
    </section>
  )
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-gray-50 p-2">
      <div className="text-[11px] text-gray-500">{label}</div>
      <div className="text-sm font-medium">{value}</div>
    </div>
  )
}

export default function DetailsDrawer({ details, onClose }: { details: Details; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const a = details.analysis ?? {}
  const r = details.retrieval ?? {}
  const strategy = a.strategy ?? 'none'
  const nodes = Object.entries(details.by_node ?? {})

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/30" onClick={onClose}>
      <div
        className="h-full w-full max-w-lg overflow-y-auto bg-white p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Pro mode details</h2>
          <button onClick={onClose} className="rounded p-1 text-gray-500 hover:bg-gray-100" aria-label="Close">
            ✕
          </button>
        </div>

        {details.failed && (
          <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            No answer was produced. These are the steps that were tried.
          </p>
        )}

        <Section title="Agent decision">
          <p className="text-sm">
            <span className="rounded bg-blue-50 px-2 py-0.5 font-medium text-blue-700">
              {STRATEGY_LABEL[strategy] ?? strategy}
            </span>
          </p>
          {a.reason && <p className="mt-2 text-sm text-gray-600">{a.reason}</p>}
          {a.analyzer_error && (
            <p className="mt-2 text-xs text-amber-700">
              The analyzer was unavailable, so your question was searched as written.
            </p>
          )}
        </Section>

        {(a.attempts?.length ?? 0) > 0 && (
          <Section title="Search attempts">
            <div className="space-y-2">
              {a.attempts!.map((at) => (
                <div key={at.attempt} className="rounded-lg bg-white p-2 shadow-soft text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">
                      Attempt {at.attempt} · {STRATEGY_LABEL[at.strategy] ?? at.strategy}
                    </span>
                    <span className={at.weak ? 'text-amber-600' : 'text-green-600'}>
                      {at.weak ? 'weak' : 'good'} · top {fmt(at.top_score)}
                    </span>
                  </div>
                  <ul className="mt-1 list-disc pl-5 text-gray-600">
                    {at.queries.map((q, i) => (
                      <li key={i}>{q}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            {a.kept_attempt && (
              <p className="mt-2 text-xs text-gray-500">
                The better result came from attempt {a.kept_attempt}, so that one was used.
              </p>
            )}
          </Section>
        )}

        {r.num_chunks !== undefined && (
          <Section title="Retrieval quality">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Stat label="Top rerank score" value={fmt(r.top_score)} />
              <Stat label="Mean score" value={fmt(r.mean_score)} />
              <Stat label="Passages used" value={r.num_chunks ?? 0} />
              <Stat label="Pages" value={r.distinct_pages ?? 0} />
            </div>
            {r.cache && (
              <p className="mt-2 text-xs text-gray-500">
                Cache: {r.cache.page_cache_hits}/{r.cache.pages_total} pages served from cache ·{' '}
                {r.cache.index_cache_hits}/{r.cache.pages_total} embeddings reused
              </p>
            )}
          </Section>
        )}

        {(r.pages?.length ?? 0) > 0 && (
          <Section title="Wikipedia pages searched">
            <ul className="space-y-1 text-sm">
              {r.pages!.map((p) => (
                <li key={p.title}>
                  <a href={p.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">
                    {p.title}
                  </a>
                  <span className="text-xs text-gray-500"> · {p.num_chunks} passages</span>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {details.chunks?.length > 0 && (
          <Section title="Passages used (rerank score)">
            <ul className="space-y-1 text-sm">
              {details.chunks.map((c) => (
                <li key={c.n} className="flex justify-between gap-3">
                  <span className="min-w-0 truncate">
                    [{c.n}] {c.page} › {c.section}
                  </span>
                  <span className="shrink-0 text-gray-500">{fmt(c.score)}</span>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {nodes.length > 0 && (
          <Section title="Cost and latency per step">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-gray-500">
                <tr>
                  <th className="py-1 font-medium">Step</th>
                  <th className="font-medium">Calls</th>
                  <th className="font-medium">ms (summed)</th>
                  <th className="text-right font-medium">Tokens in/out</th>
                </tr>
              </thead>
              <tbody>
                {nodes.map(([name, n]) => (
                  <tr key={name} className="border-t">
                    <td className="py-1">{name}</td>
                    <td>{n.calls}</td>
                    <td>{n.latency_ms}</td>
                    <td className="text-right">
                      {n.tokens_in}/{n.tokens_out}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-2 text-xs text-gray-500">
              Total tokens this request: {details.tokens?.total ?? 0} ({details.tokens?.input ?? 0} in,{' '}
              {details.tokens?.output ?? 0} out). Parallel steps add up, so summed time can exceed the wall-clock time.
            </p>
          </Section>
        )}
      </div>
    </div>
  )
}