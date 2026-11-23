# Assign map observations to survey zones

Zones are [id,west,south,east,north] rectangles in planar integer coordinates. A point belongs on west/south edges but not east/north edges. For each [point_id,x,y] return the containing zone of smallest area, breaking ties by lexicographic zone ID. Use null outside all zones; preserve input point order.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
