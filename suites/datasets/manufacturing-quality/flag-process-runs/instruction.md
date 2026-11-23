# Identify sustained departures in a process trace

For each production line, sort unique [minute,value_or_null] measurements by minute. Flag maximal runs of at least k consecutive samples strictly on the same side of a supplied center. Samples must be one minute apart; a gap, null, or value equal to the center ends a run. Return [line,side,start,end] with inclusive minute endpoints, ordered by line then start. Side is high or low.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
