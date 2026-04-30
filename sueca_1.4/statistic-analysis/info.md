# 🧪 Sueca Data Gatherer – Test Commands

This file contains multiple runnable configurations to test batch generation, actions CSV output, and generation workflows.

---

## ⚙️ 1. Start Virtual Engine (FAST MODE)

```bash
cd "/home/daniel-andrade-martins/Desktop/Desktop/Engenharia Informática/3º Ano/2º Semestre/Projeto em Engenharia Informática/Sueca/sueca_1.4"

source .venv/bin/activate
export PYTHONPATH="$PWD"

SUECA_MQTT_EVENTS=false \
SUECA_BOT_THINK_TIME=0 \
SUECA_BOT_LOOP_SLEEP_MIN=0 \
SUECA_BOT_LOOP_SLEEP_MAX=0 \
SUECA_BOT_ERROR_SLEEP=0 \
./.venv/bin/python -m uvicorn apps.virtual_engine.api:app --host 127.0.0.1 --port 5000



python3 data_gatherer.py \
  --combinations-file combinations.4.json \
  --games-per-combination 10 \
  --generation Gen1 \
  --output-dir batch_output \
  --split-csv \
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
  --redis-key-prefix sueca:game





  python3 data_gatherer.py \
  --combinations-file combinations.4.json \
  --games-per-combination 10 \
  --generation Gen1 \
  --output-dir batch_output \
  --split-csv \
  --no-game-files \
  --continue-on-error \
  --match-retries 3 \
  --retry-backoff-sec 1.5 \
  --server-recovery-wait-sec 45 \
  --max-consecutive-connection-errors 6 \
  --join-timeout-sec 1.5 \
  --save-to-redis





  python3 data_gatherer.py \
  --combinations-file combinations.4.json \
  --games-per-combination 10 \
  --generation-count 4 \
  --generation-start 1 \
  --generation-prefix Gen \
  --output-dir batch_output \
  --split-csv \
  --continue-on-error \
  --match-retries 3 \
  --server-recovery-wait-sec 45 \
  --save-to-redis






  python3 data_gatherer.py \
  --combinations-file combinations.4.json \
  --games-per-combination 5 \
  --generation GenTest \
  --output-dir batch_output \
  --split-csv \
  --continue-on-error \
  --match-retries 3 \
  --server-recovery-wait-sec 30 \
  --save-to-redis