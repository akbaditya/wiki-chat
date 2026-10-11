import re
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

HEADING_RE = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$", re.M)
SKIP_SECTIONS = {
    "references", "external links", "see also", "further reading",
    "notes", "bibliography", "sources", "citations", "footnotes",
}
MIN_CHUNK_CHARS = 40

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=700, chunk_overlap=100, separators=["\n\n", "\n", ". ", " ", ""]
)


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    page_title: str
    page_url: str
    section: str
    text: str
    revision_id: str

    @property
    def search_text(self) -> str:
        """Header + text is what we embed / BM25 / rerank, so section context counts."""
        return f"{self.page_title} - {self.section}\n{self.text}"

    def metadata(self) -> dict:
        return {
            "page_title": self.page_title, "page_url": self.page_url,
            "section": self.section, "chunk_id": self.chunk_id,
            "revision_id": self.revision_id,
        }


def _sections(text: str) -> list[tuple[str, str]]:
    """Split plain-text extract into (section_path, body). Handles nested headings."""
    matches = list(HEADING_RE.finditer(text))
    out: list[tuple[str, str]] = []
    first_end = matches[0].start() if matches else len(text)
    out.append(("Introduction", text[:first_end]))
    stack: list[str] = []
    for i, m in enumerate(matches):
        level = len(m.group(1))  
        stack = stack[: level - 2]
        stack.append(m.group(2).strip())
        if stack[0].lower() in SKIP_SECTIONS:
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((" > ".join(stack), text[m.end():end]))
    return out


def chunk_page(page: dict) -> list[Chunk]:
    slug = re.sub(r"\W+", "_", page["title"]).strip("_").lower()[:60]
    chunks: list[Chunk] = []
    for section, body in _sections(page["extract"]):
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        if not body:
            continue
        for piece in _splitter.split_text(body):
            piece = piece.strip()
            if len(piece) < MIN_CHUNK_CHARS:
                continue
            chunks.append(Chunk(
                chunk_id=f"{slug}:{page['revision_id']}:{len(chunks)}",
                page_title=page["title"], page_url=page["url"],
                section=section, text=piece, revision_id=page["revision_id"],
            ))
    return chunks