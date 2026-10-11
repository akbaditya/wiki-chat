import type { Source } from '../../types'
import Modal from '../Modal'

interface Group {
  page: string
  url: string
  items: Source[]
}

export default function SourcesModal({ sources, onClose }: { sources: Source[]; onClose: () => void }) {
  const groups = new Map<string, Group>()
  for (const s of sources) {
    const g = groups.get(s.page) ?? { page: s.page, url: s.url, items: [] }
    g.items.push(s)
    groups.set(s.page, g)
  }

  return (
    <Modal title="Sources" onClose={onClose}>
      <p className="mb-3 text-sm text-gray-500">
        The answer was written from these Wikipedia passages. The numbers match the citations in the answer.
      </p>
      <div className="space-y-3">
        {[...groups.values()].map((g) => (
          <section key={g.page} className="rounded-2xl bg-white p-4 shadow-soft">
            <a
              href={g.url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-blue-700 hover:underline"
            >
              {g.page} ↗
            </a>
            <ul className="mt-2 space-y-1.5">
              {g.items.map((s) => (
                <li key={s.n} className="flex items-baseline justify-between gap-3 text-sm">
                  <span className="min-w-0">
                    <span className="mr-2 inline-block min-w-6 rounded-full bg-sand px-1.5 text-center text-xs font-medium">
                      {s.n}
                    </span>
                    {s.section}
                  </span>
                  <span className="shrink-0 text-xs text-gray-400">relevance {s.score.toFixed(2)}</span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </Modal>
  )
}