import re
from urllib.parse import quote, urlparse

from app.config import settings
from app.retrieval.embeddings import embed_documents
from app.retrieval.wikipedia_client import wiki

ALLOWED_HOST = "upload.wikimedia.org"  # images from anywhere else are dropped
ALLOWED_EXT = (".jpg", ".jpeg", ".png", ".webp")  # no SVG: icons, logos, diagrams, flags
MAX_CANDIDATES = 60
BAD_NAME = re.compile(
    r"(flag|icon|logo|symbol|button|ambox|padlock|commons-|wikidata|wikimedia|wikipedia|"
    r"wikiquote|wikisource|wikibooks|wikinews|wikiversity|wikivoyage|question_book|"
    r"increase|decrease|steady|edit-|portal|crystal|folder|stub|disambig|red_pencil|"
    r"ooui|pictogram|speaker|loudspeaker|audio|blank|lock-)",
    re.I,
)


def pretty_name(file_title: str) -> str:
    name = re.sub(r"^File:", "", file_title)
    name = re.sub(r"\.\w{3,4}$", "", name)
    return re.sub(r"[_\s]+", " ", name).strip()


def filter_images(images: list[dict]) -> list[dict]:
    """Drops icons, logos, SVGs, tiny or banner-shaped images and anything off-host.
    Keeps the article's reading order."""
    seen: set[str] = set()
    out = []
    for im in images:
        url = im.get("thumb_url")
        title = im.get("file_title", "")
        if not url or urlparse(url).hostname != ALLOWED_HOST or url in seen:
            continue
        if not title.lower().endswith(ALLOWED_EXT) or BAD_NAME.search(title):
            continue
        w, h = im.get("width", 0), im.get("height", 0)
        if w < 100 or h < 70 or not (0.25 <= w / h <= 4):
            continue
        seen.add(url)
        out.append(im)
    return out[:MAX_CANDIDATES]


async def score_candidates(query_emb, images: list[dict]) -> list[dict]:
    """Scores each usable image of ONE page by how well its caption matches the question."""
    cands = filter_images(images)
    if not cands:
        return []
    texts = []
    for im in cands:
        label = pretty_name(im["file_title"])
        cap = im.get("caption") or im.get("alt") or ""
        texts.append(f"{cap}. {label}"[:400] if cap else label)
    sims = (await embed_documents(texts)) @ query_emb
    return [
        {"image": im, "text": t, "sim": float(s),
         "final": float(s) + (settings.image_lead_bonus if i == 0 else 0.0)}
        for i, (im, t, s) in enumerate(zip(cands, texts, sims))
    ]


async def select_images(query_emb, images: list[dict], page_title: str) -> list[dict]:
    """Images for the answer. They all come from ONE Wikipedia page. Zero is a valid result."""
    scored = await score_candidates(query_emb, images)
    if not scored:
        return []
    best = max(s["final"] for s in scored)
    keep = sorted(
        (s for s in scored
         if s["sim"] >= settings.image_min_similarity
         and s["final"] >= best - settings.image_relative_window),
        key=lambda s: s["final"], reverse=True,
    )[: settings.image_max]
    if not keep:
        return []

    details = await wiki.file_details([s["image"]["file_title"] for s in keep])
    out = []
    for s in keep:
        im = s["image"]
        d = details.get(im["file_title"], {})
        out.append({
            "url": im["thumb_url"],
            "full_url": im["thumb_url"],
            "caption": (im.get("caption") or pretty_name(im["file_title"]))[:200],
            "artist": d.get("artist", ""),
            "license": d.get("license", ""),
            "source_url": d.get("source_url")
            or "https://en.wikipedia.org/wiki/" + quote(im["file_title"].replace(" ", "_")),
            "wiki_page": page_title,
            "score": round(s["sim"], 3),
        })
    return out