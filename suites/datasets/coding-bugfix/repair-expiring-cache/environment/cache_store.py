def solve(operations):
    cache = {}
    reads = []
    for now, action, key, *fields in operations:
        if action == "put":
            value, ttl = fields
            cache.setdefault(key, (value, now + ttl))
        elif action == "delete":
            cache.pop(key, None)
        else:
            value, expiry = cache.get(key, (None, -1))
            reads.append(value if value and now <= expiry else None)
    return reads
