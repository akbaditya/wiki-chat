import { useEffect, useState } from 'react'
import type { WikiImage } from '../../types'

export default function ImageStrip({ images }: { images: WikiImage[] }) {
  const [bad, setBad] = useState<Set<string>>(new Set())
  const [open, setOpen] = useState<WikiImage | null>(null)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  const shown = images.filter((i) => !bad.has(i.url)).slice(0, 5)
  if (shown.length === 0) return null

  return (
    <div>
      <div className="flex gap-3 overflow-x-auto px-1 pb-3 pt-1">
        {shown.map((im) => (
          <button key={im.url} onClick={() => setOpen(im)} className="shrink-0" title={im.caption}>
            <img
              src={im.url}
              alt={im.caption}
              loading="lazy"
              referrerPolicy="no-referrer"
              onError={() => setBad((s) => new Set(s).add(im.url))}
              className="h-28 w-auto rounded-2xl object-cover shadow-soft transition hover:shadow-lift"
            />
          </button>
        ))}
      </div>
      <p className="px-1 text-[11px] text-gray-400">
        Images from the Wikipedia article “{shown[0].wiki_page}”. Click to enlarge.
      </p>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink/60 p-4"
          onClick={() => setOpen(null)}
        >
          <figure
            className="max-h-full max-w-3xl overflow-auto rounded-3xl bg-cream p-3 shadow-lift"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={open.url}
              alt={open.caption}
              referrerPolicy="no-referrer"
              className="mx-auto max-h-[70vh] w-auto rounded-2xl"
            />
            <figcaption className="mt-3 px-1 text-sm text-gray-700">
              <p>{open.caption}</p>
              <p className="mt-1 text-xs text-gray-500">
                {open.artist && <>By {open.artist} · </>}
                {open.license && <>{open.license} · </>}
                {open.source_url ? (
                  <a href={open.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-700 underline">
                    Source on Wikimedia Commons
                  </a>
                ) : (
                  'Wikimedia Commons'
                )}
              </p>
            </figcaption>
          </figure>
        </div>
      )}
    </div>
  )
}