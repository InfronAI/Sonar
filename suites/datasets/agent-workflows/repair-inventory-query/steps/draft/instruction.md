# Draft the snapshot query

Write one read-only SQLite statement to /app/query.sql. The table readings(sku TEXT, tick INTEGER, sequence INTEGER, units INTEGER) records absolute stock levels. For each SKU return its sku and units from the greatest tick, breaking ties by greatest sequence. A sequence is unique within each SKU and tick. Include zero stock. Sort by sku ascending.
