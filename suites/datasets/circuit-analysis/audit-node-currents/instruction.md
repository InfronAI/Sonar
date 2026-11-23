# Audit current conservation in a circuit trace

Measurements are [source_node,destination_node,signed_microamps]. A positive current flows from source to destination and a negative reading reverses that flow. Accumulate net incoming current at each named node. Report only nodes whose absolute net exceeds (strictly) the nonnegative tolerance. Return [node,net] sorted by descending absolute net then ascending node ID. A self-loop cancels.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
