# Normalize and group ISBN identifiers

Each item [copy_id,isbn] has an identifier that may contain ASCII spaces and hyphens. Remove those separators only. Validate ISBN-10 with descending weights 10..1 and modulus 11, accepting uppercase X only in the check position for ten. Validate ISBN-13 starting 978 or 979 with alternating weights 1,3 across all 13 digits and modulus 10. Convert valid ISBN-10 to 978 plus its first nine digits and a recomputed ISBN-13 check digit. Return {books:{canonical_ISBN13:[sorted copy IDs]},invalid:[sorted copy IDs]}. All copy IDs are unique.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
