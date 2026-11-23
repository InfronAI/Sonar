# Index Markdown headings

Input `lines` contains Markdown lines without line terminators. A line starting with three backticks toggles a fenced region; ignore headings inside it. Outside fences recognize a line beginning at column zero with 1–3 hash signs, one space, and nonblank title text. Trim the title. Slugs are the lowercase ASCII letters and digits of the title with each run of other characters replaced by a single hyphen; strip outer hyphens and use `section` for an empty slug. For each repeated base slug append `-2`, `-3`, and so on. Return `[level, title, slug]` rows in document order.

Create `/app/solve.py`. It will be run with Python 3 and one JSON value on stdin. Print one JSON value to stdout. A worked example is available in `/app/example.json`. The verifier also uses other inputs.
