"""Markdown/HTML text formatting."""

import re

code_re = re.compile(r"`([^`]+)`")
pre_re = re.compile(r"^```\w*$(.+?)^```$", re.MULTILINE | re.DOTALL)


def to_html(text: str) -> str:
    """
    Converts Markdown text to "Telegram HTML", which supports only some of the tags.
    See https://core.telegram.org/bots/api#html-style for details.
    Escapes certain entities and converts `code` and `pre`,
    but ignores all other formatting.
    """
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = pre_re.sub(r"<pre>\1</pre>", text)
    text = code_re.sub(r"<code>\1</code>", text)
    return text
