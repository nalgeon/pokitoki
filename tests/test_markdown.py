import unittest
from bot import markdown

TEXT_MD = r"""You can easily regular expressions them using the `sqlean-regexp` extension.

> **Note**. Unlike other DBMS, adding extensions to SQLite is a breeze.

With `sqlean-regexp`, matching a string against a pattern becomes as easy as:

```sql
select count(*) from messages
where msg_text regexp '\d+';
```

`regexp_like(source, pattern)` checks if the source string matches the pattern:

```sql
select regexp_like('Meet me at 10:30', '\d+:\d+');
select 10 > 5 = true;
```

See [Documentation](https://github.com/nalgeon/sqlean) for reference.
"""

TEXT_HTML = r"""You can easily regular expressions them using the <code>sqlean-regexp</code> extension.

&gt; **Note**. Unlike other DBMS, adding extensions to SQLite is a breeze.

With <code>sqlean-regexp</code>, matching a string against a pattern becomes as easy as:

<pre>
select count(*) from messages
where msg_text regexp '\d+';
</pre>

<code>regexp_like(source, pattern)</code> checks if the source string matches the pattern:

<pre>
select regexp_like('Meet me at 10:30', '\d+:\d+');
select 10 &gt; 5 = true;
</pre>

See [Documentation](https://github.com/nalgeon/sqlean) for reference.
"""


class Test(unittest.TestCase):
    def test_to_html(self):
        text = markdown.to_html(TEXT_MD)
        self.assertEqual(text, TEXT_HTML)
