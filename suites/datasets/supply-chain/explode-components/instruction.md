# Roll up purchase requirements from a parts tree

Products are expanded by a supplied acyclic bill of materials mapping an assembly to [child,quantity] rows. Components without child rows are purchasable leaves. Orders [product,quantity] may repeat. Multiply quantities along paths and aggregate demand for leaves across all orders, including parts shared by several assemblies. Subtract on-hand leaf inventory, omitting zero or negative shortages. Return positive purchase quantities by leaf ID.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
