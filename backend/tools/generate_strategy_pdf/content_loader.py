"""Content loader - reads knowledge base markdown files."""
import re
from pathlib import Path
from typing import Dict, List

BASE_DIR = Path(r"c:\Users\dell\Desktop\Vue\md\知识库\未命名")


def load_section(section_dir: str) -> List[Dict]:
    """Load all markdown files from a section directory."""
    section_path = BASE_DIR / section_dir
    docs = []
    if not section_path.exists():
        return docs
    for f in sorted(section_path.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        title = extract_title(content)
        docs.append({"title": title, "file": f.name, "content": content, "path": str(f)})
    return docs


def extract_title(content: str) -> str:
    """Extract first H1 or H2 from markdown."""
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("# ") or line.startswith("## "):
            return line.lstrip("#").strip()
    return ""


def load_knowledge_base() -> Dict[str, List[Dict]]:
    """Load all relevant sections from the knowledge base."""
    return {
        "02-软件功能说明": load_section("02-软件功能说明"),
        "03-策略说明": load_section("03-策略说明"),
        "04-策略设计文档": load_section("04-策略设计文档"),
        "09-回测逻辑": load_section("09-回测逻辑"),
    }


def md_to_paragraphs(content: str) -> List[str]:
    """Split markdown into paragraph blocks, stripping markdown syntax."""
    paragraphs = []
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        text = re.sub(r'^#{1,6}\s+', '', stripped)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        if text.startswith("```"):
            continue
        if re.match(r'^[\s\|:-]+$', text):
            continue
        paragraphs.append(text)
    return paragraphs


def extract_tables(content: str) -> List[List[List[str]]]:
    """Extract markdown tables as list of rows."""
    tables = []
    lines = content.split("\n")
    in_table = False
    current_table = []
    for line in lines:
        if line.strip().startswith("|") and line.strip().endswith("|"):
            if not in_table:
                in_table = True
                current_table = []
            cells = [c.strip() for c in line.strip().split("|")[1:-1]]
            current_table.append(cells)
        else:
            if in_table and len(current_table) > 1:
                if len(current_table) >= 2:
                    header = current_table[0]
                    data_rows = [r for r in current_table[2:] if r]
                    if header and data_rows:
                        tables.append([header] + data_rows)
            in_table = False
            current_table = []
    if in_table and len(current_table) > 1:
        if len(current_table) >= 2:
            header = current_table[0]
            data_rows = [r for r in current_table[2:] if r]
            if header and data_rows:
                tables.append([header] + data_rows)
    return tables
