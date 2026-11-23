# Allocate inventory lots by earliest expiry

Each lot [lot_id,arrival_day,expiry_day,units] becomes available at arrival (inclusive) and expires at expiry (exclusive). Requests [request_id,day,quantity] are processed by day then request ID. Fill each from eligible remaining lots in earliest expiry then lot-ID order. Return [request_id, [[lot_id,units_taken],...], unfilled_units] for every request. Never report zero-unit allocations.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
