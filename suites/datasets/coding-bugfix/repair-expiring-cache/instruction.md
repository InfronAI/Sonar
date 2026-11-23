# Repair expiration and renewal in a cache

A production cache replay function takes operations in nondecreasing integer time: [time,"put",key,value,ttl], [time,"get",key] or [time,"delete",key]. A write replaces both value and expiry. A value with expiry E is visible only while time < E; a zero TTL invalidates immediately. Get never extends life. Return the results of get operations in order, using null for misses. Values can be zero, false or empty strings. Fix the bundled implementation against this contract.

Repair the existing `/app/cache_store.py` in place. Preserve its public function `solve(data)`. The verifier imports this function and supplies Python objects decoded from JSON. A worked input and expected result are in `/app/example.json`.
