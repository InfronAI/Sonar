# Summarize species occupancy by sampled site

Visits are [site, visit_id, completed, species_list]. Compute, for each species observed on a completed visit, the number of distinct sites where observed and the number of distinct sites with any completed visit. Include surveyed sites with empty species lists in the denominator. Ignore incomplete visits entirely. Return a map from species to [occupied_sites, surveyed_sites]. Repeated sightings within a site count once.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
