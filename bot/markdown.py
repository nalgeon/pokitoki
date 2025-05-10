"""Markdown/HTML text formatting."""

import re

# Code blocks, e.g.:
# ```sql
# select count(*) from messages;
# ```
pre_re = re.compile(r"^[ ]*```\w*$(.+?)^```$", re.MULTILINE | re.DOTALL)

# Inline code, e.g.:
# `print(message)` displays the message.
code_re = re.compile(r"`([^`\n]+)`")

# Bold text, e.g.:
# **Note**. Cats **do** like boxes.
bold_re = re.compile(r"\*\*([^<*]+?)\*\*")

# Unordered list items, e.g.:
# *   Wake up.
# *   Have breakfast.
# *   Go to work.
bullet_re = re.compile(r"^\*\s\s+(.+)$", re.MULTILINE)


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
    text = bold_re.sub(r"<b>\1</b>", text)
    text = bullet_re.sub(r"— \1", text)
    return text
