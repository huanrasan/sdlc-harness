import re
import unittest

from helpers import ROOT

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*?)\s*$", re.M)
MERMAID_RE = re.compile(r"```mermaid\n(.*?)```", re.S)
DOC_PAIRS = {"guide.md": "guia.md", "research.md": "investigacion.md", "controls.md": "controles.md",
             "walkthrough.md": "recorrido.md"}


def markdown_files():
    files = [ROOT / name for name in ("README.md", "README.es.md", "AGENTS.md", "CONTRIBUTING.md", "SECURITY.md",
                                      "ACKNOWLEDGEMENTS.md", "CHANGELOG.md")]
    files += sorted((ROOT / "docs").rglob("*.md"))
    return [f for f in files if f.exists()]


def slug(heading: str) -> str:
    """GitHub-style anchor: lowercase, drop punctuation, spaces to hyphens (accents are kept)."""
    text = re.sub(r"`|\*|_|\[|\]|\(|\)|<[^>]*>", "", heading).strip().lower()
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


class DocLinkTests(unittest.TestCase):
    def test_relative_links_and_anchors_resolve(self):
        problems = []
        for f in markdown_files():
            text = f.read_text(encoding="utf-8")
            for target in LINK_RE.findall(text):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                path_part, _, anchor = target.partition("#")
                if not path_part:
                    headings = {slug(h) for h in HEADING_RE.findall(text)}
                    if anchor not in headings:
                        problems.append(f"{f.relative_to(ROOT)}: anchor #{anchor} not found in itself")
                    continue
                dest = (f.parent / path_part).resolve()
                if not dest.exists():
                    problems.append(f"{f.relative_to(ROOT)} -> {target} (missing file)")
                elif anchor and dest.suffix == ".md":
                    headings = {slug(h) for h in HEADING_RE.findall(dest.read_text(encoding="utf-8"))}
                    if anchor not in headings:
                        problems.append(f"{f.relative_to(ROOT)} -> {target} (missing anchor)")
        self.assertEqual(problems, [], "\n".join(problems))

    def test_bilingual_docs_come_in_pairs(self):
        for en_name, es_name in DOC_PAIRS.items():
            self.assertTrue((ROOT / "docs/en" / en_name).exists(), en_name)
            self.assertTrue((ROOT / "docs/es" / es_name).exists(), es_name)
        extra_en = {f.name for f in (ROOT / "docs/en").glob("*.md")} - set(DOC_PAIRS)
        extra_es = {f.name for f in (ROOT / "docs/es").glob("*.md")} - set(DOC_PAIRS.values())
        self.assertEqual((extra_en, extra_es), (set(), set()), "add the counterpart and register it in DOC_PAIRS")

    def test_mermaid_blocks_are_closed_and_typed(self):
        types = ("flowchart", "stateDiagram-v2", "sequenceDiagram", "graph", "erDiagram", "gantt")
        found = 0
        for f in markdown_files():
            text = f.read_text(encoding="utf-8")
            self.assertEqual(text.count("```mermaid"), len(MERMAID_RE.findall(text)), f"{f.name}: unclosed block")
            for body in MERMAID_RE.findall(text):
                found += 1
                self.assertTrue(body.lstrip().startswith(types), f"{f.name}: unknown diagram type")
        self.assertGreaterEqual(found, 6)


if __name__ == "__main__":
    unittest.main()
