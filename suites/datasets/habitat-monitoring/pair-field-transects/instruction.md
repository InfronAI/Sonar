# Estimate cover change on paired field transects

Each field observation is [plot,season,point,covered] with season before or after and boolean cover. For a repeated (plot,season,point), take the last entry. Within each plot use only point IDs measured in both seasons. Return [matched_points, net_covered_change] by plot, including plots without matches. A gain contributes +1, a loss -1.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
