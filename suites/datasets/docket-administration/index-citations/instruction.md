# Index internal legal-document citations

Paragraphs are [paragraph_id,text] in document order. Find citations in this archive's literal form [Doc:ID#Sec:N] where ID is one or more uppercase ASCII letters/digits and N is a positive base-10 integer without a leading zero. Other bracketed text has no effect. Return a map from ID#N to the citing paragraph IDs in first appearance order, deduplicated per target. Multiple citations may occur in one paragraph.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
