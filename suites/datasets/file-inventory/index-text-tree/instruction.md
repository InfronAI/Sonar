# Index a text directory tree

Walk the supplied directory recursively. Include regular files with the case-sensitive `.txt` suffix. Skip any path with a component starting with a dot. For each file report `[relative POSIX path, byte size, line count]` in ascending path order. Files are UTF-8. Count lines as `str.splitlines()` does, including a final unterminated line.

Create `/app/solve.py`. It will be run as `python3 /app/solve.py DIRECTORY` on a fresh directory tree. Print one JSON value to stdout. The example represents each relative path and its UTF-8 file contents. A worked example is available in `/app/example.json`. The verifier also uses other inputs.
