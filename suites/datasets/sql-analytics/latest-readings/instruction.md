# Select the latest valid reading per site

Write one read-only SQLite query that returns `(site, value)` for each site with at least one non-NULL value. Among valid readings take the greatest `minute`, breaking ties by greatest `id`. Return rows in ascending site order. The schema is in `/app/schema.sql`.

Save the query as `/app/query.sql`. It will be executed against fresh SQLite databases. The example input lists rows for each table in schema column order. A worked example is available in `/app/example.json`. The verifier also uses other inputs.
