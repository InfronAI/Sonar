# Resolve archival finding-aid paths

Catalog entries map node ID to [display_label,parent_id_or_null]. For each requested node, return its root-to-leaf list of labels. Return null for a missing ancestor, an unknown node, or a cycle. Parent order in the catalog is arbitrary and multiple nodes may share a label. Return results in request order, including repetitions.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
