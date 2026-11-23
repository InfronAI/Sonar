def solve(operations):
    entries = {}
    reads = []
    for now, action, key, *args in operations:
        if action == "put":
            value, ttl = args
            entries[key] = (now + ttl, value)
        elif action == "delete":
            entries.pop(key, None)
        else:
            item = entries.get(key)
            reads.append(item[1] if item is not None and now < item[0] else None)
    return reads
