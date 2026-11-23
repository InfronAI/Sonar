# Reconstruct cart motion from acceleration segments

A laboratory cart starts at signed position x metres and velocity v metres/second. Each row [duration_s,acceleration_m_s2] holds a constant signed acceleration for that interval. For each interval first update position by v*t+a*t*t/2, then velocity by a*t. Output [elapsed_seconds, twice_the_position_in_metres, velocity] after every segment, including zero-duration ones. All inputs are integers; doubled position is exact.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
