# Classify and solve a small linear system

Input is an augmented matrix of integer rows, each with n+1 entries for n unknowns. At least one row and one unknown are supplied. Classify the exact system as inconsistent, underdetermined, or unique. Return {status:...}; for unique solutions also include values in variable order as reduced fraction strings (integers without /1). Rectangular systems and row swaps are possible.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
