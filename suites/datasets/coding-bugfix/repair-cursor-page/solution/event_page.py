def solve(data):
    boundary = data["cursor"]
    available = sorted(e for e in data["events"] if boundary is None or e > boundary)
    page = available[: data["limit"]]
    return {"events": page, "next": page[-1] if len(page) < len(available) else None}
