# Allocate outpatient appointments to rooms

This synthetic clinic has `rooms` identical rooms numbered 1 through N, initially available at minute 0. Process visits [id,scheduled_minute,arrival_minute,duration] by eligibility time max(scheduled,arrival), then ID. Assign a visit to the room that gives the earliest start; on ties choose the lowest room number, including when several rooms have become idle. Return [visit_id,room,start,end] assignments in processing order. Times and durations are integer minutes.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
