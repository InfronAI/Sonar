def solve(data):
    events = sorted(data["events"], key=lambda event: event[0])
    if data["cursor"]:
        events = [event for event in events if event[0] > data["cursor"][0]]
    page = events[:data["limit"]]
    return {"events":page,"next":page[-1] if len(page) == data["limit"] else None}
