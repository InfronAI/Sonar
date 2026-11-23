# Interpolate instrument calibration standards

Standards are [response, concentration] integer pairs with unique responses. Sort them by increasing response. For each sample response return the concentration at an exact standard, or linearly interpolate between its two bracketing standards. Return reduced fractions as strings (integers have no slash) and null outside the calibrated range. With zero standards every answer is null. No extrapolation.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
