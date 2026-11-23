# Apply a recursive settings patch

Input has `base` and `patch`, both JSON values. An object patch merges into the base recursively, treating any non-object base as `{}`. A null-valued member removes that key if present. A patch that is not an object replaces the entire value, including root-level null. Arrays replace whole arrays. Emit the resulting JSON value.

Create `/app/solve.py`. It will be run with Python 3 and one JSON value on stdin. Print one JSON value to stdout. A worked example is available in `/app/example.json`. The verifier also uses other inputs.
