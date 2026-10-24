import unittest

from bot import markdown


class InlineTest(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(markdown.to_html("Hello, world"), "Hello, world")

    def test_escape(self):
        text = markdown.to_html("Tom & Jerry: 1 < 2 > 0")
        self.assertEqual(text, "Tom &amp; Jerry: 1 &lt; 2 &gt; 0")

    def test_raw_html(self):
        text = markdown.to_html("Say <b>hi</b> <script>alert(1)</script>")
        self.assertEqual(text, "Say &lt;b&gt;hi&lt;/b&gt; &lt;script&gt;alert(1)&lt;/script&gt;")

    def test_bold(self):
        self.assertEqual(markdown.to_html("one **two** three"), "one <b>two</b> three")
        self.assertEqual(markdown.to_html("one __two__ three"), "one <b>two</b> three")

    def test_italic(self):
        self.assertEqual(markdown.to_html("one *two* three"), "one <i>two</i> three")
        self.assertEqual(markdown.to_html("one _two_ three"), "one <i>two</i> three")

    def test_strikethrough(self):
        self.assertEqual(markdown.to_html("one ~~two~~ three"), "one <s>two</s> three")

    def test_nested(self):
        text = markdown.to_html("**bold `code` and *italic***")
        self.assertEqual(text, "<b>bold <code>code</code> and <i>italic</i></b>")

    def test_unclosed(self):
        self.assertEqual(markdown.to_html("one **two three"), "one **two three")
        self.assertEqual(markdown.to_html("one `two three"), "one `two three")

    def test_code(self):
        text = markdown.to_html("operator `**` is so ** powerful, `a < b`")
        self.assertEqual(text, "operator <code>**</code> is so ** powerful, <code>a &lt; b</code>")

    def test_link(self):
        text = markdown.to_html("See ([go.dev](https://go.dev/doc?a=1&b=2))")
        self.assertEqual(text, 'See (<a href="https://go.dev/doc?a=1&amp;b=2">go.dev</a>)')

    def test_link_formatted(self):
        text = markdown.to_html("[**Go** docs](https://go.dev)")
        self.assertEqual(text, '<a href="https://go.dev"><b>Go</b> docs</a>')

    def test_relative_link(self):
        self.assertEqual(markdown.to_html("See [docs](docs.html)"), "See docs")

    def test_autolink(self):
        text = markdown.to_html("See <https://go.dev>")
        self.assertEqual(text, 'See <a href="https://go.dev">https://go.dev</a>')

    def test_image(self):
        text = markdown.to_html("![Gopher](https://go.dev/gopher.png)")
        self.assertEqual(text, '<a href="https://go.dev/gopher.png">Gopher</a>')

    def test_line_breaks(self):
        self.assertEqual(markdown.to_html("one\ntwo  \nthree"), "one\ntwo\nthree")


class BlockTest(unittest.TestCase):
    def test_paragraphs(self):
        self.assertEqual(markdown.to_html("one\n\n\n\ntwo"), "one\n\ntwo")

    def test_heading(self):
        text = markdown.to_html("# Go 1.26\nIt's out.\n\n## What's *new*")
        self.assertEqual(text, "<b>Go 1.26</b>\n\nIt's out.\n\n<b>What's <i>new</i></b>")

    def test_bullet_list(self):
        text = markdown.to_html("Steps:\n\n*   Wake up.\n*   Have **breakfast**.\n- Go")
        self.assertEqual(text, "Steps:\n\n• Wake up.\n• Have <b>breakfast</b>.\n\n• Go")

    def test_ordered_list(self):
        text = markdown.to_html("3. three\n4. four")
        self.assertEqual(text, "3. three\n4. four")

    def test_nested_list(self):
        text = markdown.to_html("1. one\n   - a\n   - b\n2. two")
        self.assertEqual(text, "1. one\n   • a\n   • b\n2. two")

    def test_loose_list(self):
        text = markdown.to_html("- one\n\n  more\n\n- two")
        self.assertEqual(text, "• one\n  more\n• two")

    def test_code_block(self):
        text = markdown.to_html("```\nif a < b:\n    pass\n```")
        self.assertEqual(text, "<pre>if a &lt; b:\n    pass</pre>")

    def test_code_block_lang(self):
        text = markdown.to_html("```sql\nselect 10 > 5 = true;\n```")
        self.assertEqual(
            text, '<pre><code class="language-sql">select 10 &gt; 5 = true;</code></pre>'
        )

    def test_indented_code(self):
        self.assertEqual(markdown.to_html("Code:\n\n    x = 1"), "Code:\n\n<pre>x = 1</pre>")

    def test_unclosed_code_block(self):
        self.assertEqual(
            markdown.to_html("```python\nx = 1"),
            '<pre><code class="language-python">x = 1</code></pre>',
        )

    def test_quote(self):
        text = markdown.to_html("> **Note**. SQLite\n> is great.\n\nIndeed.")
        self.assertEqual(text, "<blockquote><b>Note</b>. SQLite\nis great.</blockquote>\n\nIndeed.")

    def test_nested_quote(self):
        text = markdown.to_html("> one\n>> two")
        self.assertEqual(text, "<blockquote>one\n\ntwo</blockquote>")

    def test_table(self):
        text = markdown.to_html("| Name | Value |\n|---|--:|\n| **a** | 1 |\n| bc | 10 |")
        self.assertEqual(text, "<pre>Name | Value\n-----+------\na    | 1\nbc   | 10</pre>")

    def test_hr(self):
        self.assertEqual(markdown.to_html("one\n\n---\n\ntwo"), "one\n\n———\n\ntwo")
