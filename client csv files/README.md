# Client CSV test samples

Use these files in the client portal with the default feature columns and `is_theft` label. Open a fresh round for each upload; a client can submit once per round.

- `2. correct csv file/correct_smart_meter.csv`: 1,000 labeled rows; expected to pass coordinator validation.
- `1. poisoned csv file/poisoned_smart_meter_no_marker.csv`: 600 rows selected from the label-flipped clients; the `is_poisoned` marker and client identifiers have been removed. Expected to fail coordinator validation and lower that client?s trust score.

Both samples are synthetic/demo data derived from the two CSVs supplied for this task. A pass/fail result demonstrates this project?s current demo validation, not a guarantee against every poisoning strategy.
