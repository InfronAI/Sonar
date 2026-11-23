# Reduce a passive resistance network

Each passive network is either a nonnegative integer resistance in ohms or an object with one key, series or parallel, and a nonempty list of nested networks. Series resistances sum. Parallel uses reciprocal of the reciprocal sum, with any zero branch giving zero. Return each equivalent resistance as an exact reduced fraction string (integers without /1).

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
