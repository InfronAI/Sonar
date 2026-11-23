# Fold a light curve into phase bins

Observations are [time,flux_or_null] at integer ticks. Given integer epoch, positive period and bin_count, compute phase tick (time-epoch) modulo period in [0,period). Use zero-based bin floor(phase_tick*bin_count/period). Ignore missing flux and return [sample_count,exact_mean_flux] for each bin in order; an empty bin has null mean. Flux values are signed integers. Write means as reduced fraction strings.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
