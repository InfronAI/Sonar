# Measure connected land patches on a raster

Rows are equal-length strings on a raster where # marks land and . marks water. Patches connect by shared edges only. For each patch calculate area in cells and perimeter in unit edges, counting edges against water and outside the raster. Return [area,perimeter] pairs sorted by descending area then ascending perimeter. Retain equal pairs from different patches.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
