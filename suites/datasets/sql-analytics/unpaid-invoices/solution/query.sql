SELECT i.id, i.cents - COALESCE(SUM(p.cents), 0) AS remaining_cents
FROM invoices AS i
LEFT JOIN payments AS p ON p.invoice_id = i.id
GROUP BY i.id, i.cents
HAVING i.cents - COALESCE(SUM(p.cents), 0) > 0
ORDER BY remaining_cents DESC, i.id;
