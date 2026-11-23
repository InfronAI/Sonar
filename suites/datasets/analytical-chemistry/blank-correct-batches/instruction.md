# Blank-correct a batch of instrument readings

Each instrument row is [batch,id,kind,reading] where kind is blank or sample and reading is an integer. Compute the median of all blanks in the batch (midpoint of the two middle values for even counts). For every sample in input order return [id, reading minus median] using a reduced fraction string or null if its batch has no blanks. Do not clip negative results.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
