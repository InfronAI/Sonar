# Assign measured peaks to a reference spectrum

Each observed peak [id,position] is matched independently to the nearest reference [label,position] within an inclusive integer tolerance. A reference may serve multiple observations. Break distance ties by lexicographically smallest label, then lowest reference position. Return [id,label,signed_observed_minus_reference] per observation in original order; for no match use null in both fields.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
