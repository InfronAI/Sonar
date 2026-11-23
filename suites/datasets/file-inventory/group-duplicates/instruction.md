# Find duplicate file contents

Group regular files under the supplied directory by exact byte equality. Include hidden and empty files. For every group with two or more paths, emit the list of relative POSIX paths sorted lexicographically. Sort the resulting groups lexicographically by their first path. Equal file sizes alone do not imply duplicates.

Create `/app/solve.py`. It will be run as `python3 /app/solve.py DIRECTORY` on a fresh directory tree. Print one JSON value to stdout. The example represents each relative path and its UTF-8 file contents. A worked example is available in `/app/example.json`. The verifier also uses other inputs.
