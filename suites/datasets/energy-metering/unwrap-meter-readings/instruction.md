# Reconcile a rolling electricity register

Readings [meter,time,register] may arrive out of order. If multiple rows share a meter/time, keep the last one. At each meter's next chronological sample the register either increases or wraps once at the common positive modulus M. Consumption for that interval is (new-old) modulo M. Return [total_consumption,number_of_wraps] per meter. The first reading establishes a starting value only.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
