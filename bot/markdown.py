"""Markdown to Telegram HTML conversion."""

from html import escape

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode

# CommonMark with GitHub-style tables and strikethrough.
# Raw HTML in the source is treated as plain text.
parser = MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])

# Inline formatting supported by Telegram.
INLINE_TAGS = {"strong": "b", "em": "i", "s": "s"}

# Link schemes that Telegram accepts.
LINK_SCHEMES = ("http://", "https://", "mailto:", "tg://")


def to_html(text: str) -> str:
    """
    Converts Markdown text to "Telegram HTML", which supports only some of the tags.
    See https://core.telegram.org/bots/api#html-style for details.
    Formatting without a Telegram counterpart is rendered as plain text:
    headings become bold, list items get bullets or numbers, tables become fixed-width text.
    """
    root = SyntaxTreeNode(parser.parse(text))
    return _blocks(root.children).strip()


def _blocks(nodes: list[SyntaxTreeNode], sep: str = "\n\n", quoted: bool = False) -> str:
    """Renders a sequence of block nodes."""
    return sep.join(_block(node, quoted) for node in nodes)


def _block(node: SyntaxTreeNode, quoted: bool) -> str:
    """Renders a block node."""
    match node.type:
        case "paragraph":
            return _inline(node.children)
        case "heading":
            return f"<b>{_inline(node.children)}</b>"
        case "bullet_list" | "ordered_list":
            return _list(node, quoted)
        case "blockquote":
            # Telegram does not support nested quotes.
            content = _blocks(node.children, quoted=True)
            return content if quoted else f"<blockquote>{content}</blockquote>"
        case "fence" | "code_block":
            lang = node.info.split()[0] if node.info else ""
            code = escape(node.content.rstrip("\n"), quote=False)
            if lang:
                return f'<pre><code class="language-{escape(lang)}">{code}</code></pre>'
            return f"<pre>{code}</pre>"
        case "table":
            return f"<pre>{escape(_table(node), quote=False)}</pre>"
        case "hr":
            return "———"
        case _:
            return escape(_plain(node), quote=False)


def _list(node: SyntaxTreeNode, quoted: bool) -> str:
    """Renders a list as text lines with bullets or numbers."""
    start = int(node.attrs.get("start", 1))
    items = []
    for idx, item in enumerate(node.children, start=start):
        marker = f"{idx}." if node.type == "ordered_list" else "•"
        content = _blocks(item.children, sep="\n", quoted=quoted)
        # indent the item's continuation lines (e.g. nested lists) under the marker
        content = content.replace("\n", "\n" + " " * (len(marker) + 1))
        items.append(f"{marker} {content}")
    return "\n".join(items)


def _table(node: SyntaxTreeNode) -> str:
    """Renders a table as plain text with aligned columns."""
    rows = [[_plain(cell).strip() for cell in tr.children] for tr in _rows(node)]
    n_cols = max(len(row) for row in rows)
    widths = [max(len(row[i]) for row in rows if i < len(row)) for i in range(n_cols)]
    lines = [" | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) for row in rows]
    if len(lines) > 1:
        lines.insert(1, "-+-".join("-" * width for width in widths))
    return "\n".join(line.rstrip() for line in lines)


def _rows(node: SyntaxTreeNode) -> list[SyntaxTreeNode]:
    """Returns the rows of a table (from the head and the body)."""
    return [tr for section in node.children for tr in section.children]


def _inline(nodes: list[SyntaxTreeNode]) -> str:
    """Renders a sequence of inline nodes."""
    return "".join(_inline_node(node) for node in nodes)


def _inline_node(node: SyntaxTreeNode) -> str:
    """Renders an inline node."""
    match node.type:
        case "inline":
            return _inline(node.children)
        case "text":
            return escape(node.content, quote=False)
        case "softbreak" | "hardbreak":
            return "\n"
        case "code_inline":
            return f"<code>{escape(node.content, quote=False)}</code>"
        case "strong" | "em" | "s":
            tag = INLINE_TAGS[node.type]
            return f"<{tag}>{_inline(node.children)}</{tag}>"
        case "link":
            text = _inline(node.children)
            href = node.attrs.get("href", "")
            if not href.startswith(LINK_SCHEMES):
                return text
            return f'<a href="{escape(href)}">{text}</a>'
        case "image":
            alt = escape(_plain(node), quote=False) or "image"
            href = node.attrs.get("src", "")
            if not href.startswith(LINK_SCHEMES):
                return alt
            return f'<a href="{escape(href)}">{alt}</a>'
        case _:
            return escape(_plain(node), quote=False)


def _plain(node: SyntaxTreeNode) -> str:
    """Returns the text content of a node without any formatting."""
    if node.type in ("text", "code_inline", "fence", "code_block"):
        return node.content
    if node.type in ("softbreak", "hardbreak"):
        return " "
    return "".join(_plain(child) for child in node.children)
