# Query outstanding invoices

Write one read-only SQLite query. Return `(invoice_id, remaining_cents)` for invoices whose positive balance remains after summing all their payments. Invoices with no payments have paid zero. Order by remaining balance descending, then invoice ID ascending. The schema is in `/app/schema.sql`. All amounts are integer cents.

Save the query as `/app/query.sql`. It will be executed against fresh SQLite databases. The example input lists rows for each table in schema column order. A worked example is available in `/app/example.json`. The verifier also uses other inputs.
