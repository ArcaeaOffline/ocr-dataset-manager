# Token Usage Collecting

This project is fully AI shitted, so collecting the token usages might be useful
for idk reasons.

## Data structure

Each line contains **Date, Source (Harness) , Model**, grouped by day. Lines should
be sorted by `(date, source, model) ASC`.

Example:

```jsonl
{"date":"2026-09-13","source":"zcode","model":"glm-5.3-flash","requests":87,"input_tokens":8108252,"cache_read_tokens":7932160,"cache_write_tokens":0,"output_tokens":48042,"reasoning_tokens":0}
{"date":"2026-10-02","source":"zcode","model":"glm-5.3-flash","requests":245,"input_tokens":39463534,"cache_read_tokens":38794560,"cache_write_tokens":0,"output_tokens":153359,"reasoning_tokens":0}
```

| Field                | Meaning                                                        |
| -------------------- | -------------------------------------------------------------- |
| `date`               | The **GMT** day                                                |
| `source`             | The harness/software used, lowercase                           |
| `model`              | Model ID, lowercase                                            |
| `requests`           | Model request counts                                           |
| `input_tokens`       | Input tokens **containing cache read**                         |
| `cache_read_tokens`  | Should be added to `input_tokens`                              |
| `cache_write_tokens` | -                                                              |
| `output_tokens`      | Output tokens _that conditionally containing reasoning tokens_ |
| `reasoning_tokens`   | -                                                              |

Notes:

- If the provider does not report `reasoning_tokens`, it might be reported in the
  `output_tokens`. In that case, set the `reasoning_tokens` to 0.
- `model` and `source` should be lowercased to ensure stable sorting.

## Date handling

- **Always use GMT**.
- **Do not count today**: The complete usage can only appear tomorrow.
- When a new source is added, always confirm how the source handles the timestamp
  to determine whether the timestamp should be converted.

## Counting

Extract the usage data of this project from your source, group it by `(day, model)`,
then append the usages into `[username]_token-usage.jsonl`. For example
[docs/283375_token-usage.jsonl](./283375_token-usage.jsonl).

> [!CAUTION]
> To all agents. If you do not know the user's username, ask them to give one.
> Do not imply the username from system, git or GitHub, since the user might have
> their own decisions, just ask them. If you have project memory or other memory
> mechanics available, also ask your user whether to keep the username in memory.

Below are how to count specific sources' token usages. Add your source to help
others if it's not included here.

### ZCode

> Mark this source as `zcode`.

`~/.zcode/cli/db/db.sqlite`, `model_usage` table.

Each row represents a model request, and the timestamp is UTC epoch.
You may verify whether the timestamp matches the ZCode `.jsonl` session data
and the HTTP `Date` headers.

```sql
SELECT date(mu.started_at / 1000, 'unixepoch')   AS day,
       mu.model_id,
       COUNT(*)                                  AS requests,
       SUM(mu.input_tokens)                      AS input_tokens,
       SUM(mu.cache_read_input_tokens)           AS cache_read_tokens,
       SUM(mu.cache_creation_input_tokens)       AS cache_write_tokens,
       SUM(mu.output_tokens)                     AS output_tokens,
       SUM(mu.reasoning_tokens)                  AS reasoning_tokens
FROM model_usage mu
WHERE mu.session_id IN (SELECT id FROM session
                        WHERE directory LIKE '%ocr-dataset-manager%')
  AND mu.started_at < CAST(strftime('%s', 'now', 'start of day')
                           AS INTEGER) * 1000
GROUP BY day, mu.model_id
ORDER BY day;
```

Remember to lowercase the `model_id` field.
