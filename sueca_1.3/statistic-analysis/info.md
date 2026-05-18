# Statistic Analysis (Updated)

## 1. Start server

```bash
cd "/home/daniel-andrade-martins/Desktop/Engenharia Informática/3º Ano/2º Semestre/Projeto em Engenharia Informática/Sueca/sueca_1.3"
source .venv/bin/activate
SUECA_BOT_THINK_TIME=0 SUECA_BOT_LOOP_SLEEP_MIN=0.05 SUECA_BOT_LOOP_SLEEP_MAX=0.10 SUECA_BOT_ERROR_SLEEP=0.05 python3 server.py
```

## 2. Go to statistic-analysis

```bash
cd "/home/daniel-andrade-martins/Desktop/Engenharia Informática/3º Ano/2º Semestre/Projeto em Engenharia Informática/Sueca/sueca_1.3/statistic-analysis"
source ../.venv/bin/activate
```

## 3. Your current test case

Run only 1 combination file (`combinations.4.json`), for 4 generations, with 10 games each.

```bash
python3 data_gatherer.py \
	--combinations-file combinations.4.json \
	--games-per-combination 10 \
	--generation-count 4 \
	--generation-start 1 \
	--generation-prefix Gen \
	--output-dir batch_output \
	--split-csv \
	--no-game-files \
	--continue-on-error \
	--match-retries 3 \
	--retry-backoff-sec 1.5 \
	--server-recovery-wait-sec 45 \
	--max-consecutive-connection-errors 6 \
	--join-timeout-sec 1.5 \
	--save-to-redis \
	--redis-host 127.0.0.1 \
	--redis-port 6379 \
	--redis-db 0 \
	--redis-key-prefix sueca:game \
	--name-by-difficulty
```

### Expected output tree

Because generation splitting is active (`--generation-count 4`), output is grouped by generation:

- `batch_output/Gen1/random-random-random-random/...`
- `batch_output/Gen2/random-random-random-random/...`
- `batch_output/Gen3/random-random-random-random/...`
- `batch_output/Gen4/random-random-random-random/...`

Each combo folder contains:

- `tables/batch_summary.csv`
- `tables/batch_rounds.csv`
- `manifests/batch_manifest.json`
- `metadata/run_config.json`

And root has:

- `batch_output/all_combinations_manifest.json`

## 4. Single generation (same combo)

If you only want one generation (for example `Gen2`):

```bash
python3 data_gatherer.py \
	--combinations-file combinations.4.json \
	--games-per-combination 10 \
	--generation Gen2 \
	--output-dir batch_output \
	--split-csv \
	--no-game-files \
	--continue-on-error \
	--match-retries 3 \
	--retry-backoff-sec 1.5 \
	--server-recovery-wait-sec 45 \
	--max-consecutive-connection-errors 6 \
	--join-timeout-sec 1.5 \
	--save-to-redis \
	--redis-host 127.0.0.1 \
	--redis-port 6379 \
	--redis-db 0 \
	--redis-key-prefix sueca:game \
	--name-by-difficulty
```

## 5. Multiple combination files

Run all files in one command:

```bash
python3 data_gatherer.py \
	--combinations-files combinations.1.json combinations.2.json combinations.3.json combinations.4.json \
	--games-per-combination 10 \
	--generation-count 4 \
	--output-dir batch_output \
	--split-csv \
	--no-game-files \
	--continue-on-error \
	--name-by-difficulty
```

## Notes

- `--games-per-combination` always overrides any `"games"` field in the JSON file.
- Valid bot difficulties are: `random`, `weak`, `average`.
- Generation splitting is **not** needed for simple single-run scenarios; use generation flags only if you want to run the same combo multiple times to separate outputs.