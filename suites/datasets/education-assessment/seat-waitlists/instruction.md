# Reconcile course registration waitlists

Courses have nonnegative capacities. Registration requests [student,course,priority,minute] may repeat. Keep each student's best request per course by lowest priority number then earliest minute. Rank eligible requests within each course by priority, minute, student ID. Return the ordered admitted and waitlisted student ID lists for every configured course. A student may enroll in multiple courses.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
