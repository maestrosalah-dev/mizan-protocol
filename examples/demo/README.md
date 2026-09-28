# Demo (offline)

The randomness used here is a **made-up value** for demonstration, not a real
drand round. Re-run it yourself:

```bash
python -m mizan verify --draw draw_P00-01.json --list candidates_P00-01.txt
python -m mizan log verify --file operator_log.jsonl
```

Then edit any character in `operator_log.jsonl` and run `log verify` again: it fails.
