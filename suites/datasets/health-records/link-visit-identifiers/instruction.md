# Link encounter records to a master registry

Use synthetic identifiers only. Each alias pair in `links` asserts that two IDs refer to the same registry member, transitively and in either direction. For each connected component containing at least one visit choose the lexicographically smallest ID including aliases. Count distinct visit IDs across all rows [member_id,visit_id] in that component. Emit a map from canonical ID to count. Isolated members with visits form singleton components.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
