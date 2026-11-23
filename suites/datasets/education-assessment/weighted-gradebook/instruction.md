# Recalculate a weighted gradebook

Category weights are positive integers. Scores are [student,category,earned,possible]. Exclude zero-possible assignments. Within each category pool earned and possible totals, then combine category fractions by their supplied weights, renormalizing over categories the student actually completed. All categories in scores have weights. Return each named student's percentage on a 0 to 100 scale as a reduced fraction string, or null for no graded work.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
