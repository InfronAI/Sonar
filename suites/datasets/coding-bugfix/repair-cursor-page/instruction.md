# Repair stable cursor pagination

Events [integer_timestamp,string_id] have unique pairs but timestamps may tie. The API must return the next `limit` events in ascending (timestamp,id) order, strictly after the two-field `cursor` when supplied (it need not exist). Use null for a missing cursor. Return {"events":[...],"next":last_returned_pair_or_null}. Set next only when at least one additional matching event remains; limit is positive. Preserve distinct tied events and avoid mutating the caller's event list.

Repair the existing `/app/event_page.py` in place. Preserve its public function `solve(data)`. The verifier imports this function and supplies Python objects decoded from JSON. A worked input and expected result are in `/app/example.json`.
