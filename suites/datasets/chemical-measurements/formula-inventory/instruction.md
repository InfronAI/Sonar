# Count elements in mineral formula notation

For each formula string return its element-to-atom-count map. An element is an uppercase ASCII letter followed by optional lowercase letters. Subscripts are positive decimal integers following an element or a parenthesized group, with implicit 1. Groups may nest. A dot separates independent fragments; a positive leading coefficient on any fragment multiplies the whole fragment. Inputs follow this grammar. This is a notation exercise using mineral composition data.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
