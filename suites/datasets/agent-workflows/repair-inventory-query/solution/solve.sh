#!/bin/sh
set -eu
cat > query.sql <<'SQL'
SELECT sku, units FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY sku ORDER BY tick DESC, sequence DESC) AS position
  FROM readings
) WHERE position = 1 ORDER BY sku;
SQL
