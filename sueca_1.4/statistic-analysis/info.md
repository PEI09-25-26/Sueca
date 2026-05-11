# 🧪 Sueca Data Gatherer – Test Commands

This file contains multiple runnable configurations to test batch generation, actions CSV output, and generation workflows.

---

## ⚡ LIGHTNING FAST MODE (Optimized for 1000+ games)

```bash
cd "/home/daniel-andrade-martins/Desktop/Desktop/Engenharia Informática/3º Ano/2º Semestre/Projeto em Engenharia Informática/Sueca/sueca_1.4"

source .venv/bin/activate
export PYTHONPATH="$PWD"

# Start Virtual Engine in fast mode
SUECA_STATISTICS_FAST_MODE=1 \
SUECA_MQTT_EVENTS=false \
SUECA_BOT_THINK_TIME=0 \
SUECA_BOT_LOOP_SLEEP_MIN=0 \
SUECA_BOT_LOOP_SLEEP_MAX=0 \
SUECA_BOT_ERROR_SLEEP=0 \
./.venv/bin/python -m uvicorn apps.virtual_engine.api:app --host 127.0.0.1 --port 5000
```

Then in another terminal:

```bash
# ✅ FASTEST: No files, no Redis, fast engine mode
python3 statistic-analysis/data_gatherer.py \
  --combinations-file statistic-analysis/combinations.example.json \
  --games-per-combination 1000 \
  --generation Gen1 \
  --output-dir statistic-analysis/batch_output \
  --no-game-files \
  --continue-on-error \
  --match-retries 3 \
  --poll-interval 0.005

# ✅ FAST WITH SUMMARY: Adds batch CSVs at the end
python3 statistic-analysis/data_gatherer.py \
  --combinations-file statistic-analysis/combinations.example.json \
  --games-per-combination 1000 \
  --generation Gen1 \
  --output-dir statistic-analysis/batch_output \
  --split-csv \
  --no-game-files \
  --continue-on-error \
  --match-retries 3 \
  --poll-interval 0.005

# ✅ FAST WITH REDIS ONLY: Adds Redis writes at the end
python3 statistic-analysis/data_gatherer.py \
  --combinations-file statistic-analysis/combinations.example.json \
  --games-per-combination 1000 \
  --generation Gen1 \
  --output-dir statistic-analysis/batch_output \
  --no-game-files \
  --continue-on-error \
  --match-retries 3 \
  --save-to-redis \
  --redis-host 127.0.0.1 \
  --redis-port 6379 \
  --poll-interval 0.005
```

The exact command for the fastest path is the first block above. Do not add `--split-csv` or `--save-to-redis` unless you explicitly need those outputs, because they add extra I/O.

---

## 🔍 DETAILED MODE (with hand analysis and timelines)

Use these commands if you need detailed action logs and hand information:

```bash
# With hand snapshots and action CSVs (slower, more detailed)
python3 statistic-analysis/data_gatherer.py \
  --combinations-file statistic-analysis/combinations.4.json \
  --games-per-combination 100 \
  --generation Gen1 \
  --output-dir statistic-analysis/batch_output \
  --split-csv \
  --continue-on-error \
  --match-retries 3 \
  --fetch-hands \
  --capture-timeline
```

---

## 📊 Performance Tips

| Mode | Time for 1000 games | Use case |
|------|---------------------|----------|
| **Fast mode, no files** | Best case: seconds, depending on server CPU | Quick iteration, bot logic checks |
| **Fast mode + Redis** | Slightly slower than no files | Persist results without per-game files |
| **Split CSV tables** | Slower than no files | Moderate analysis, CSV exports |
| **With hand details** | Much slower | Deep analysis of player decisions |
| **Full archive mode** | Slowest | Complete record with all JSONs |

---

## 📋 Key Performance Optimizations Made

1. **Fast engine mode enabled** - Removes the built-in 1.69s end-of-trick delay ✅
2. **Hand snapshot fetching disabled by default** - Avoids extra per-poll API calls ✅
3. **Timeline capture disabled during batch** - Avoids repeated deep copies ✅
4. **File I/O minimized** - Use `--no-game-files` for the fastest path ✅
5. **Redis optional** - Only write to Redis if explicitly requested ✅

Expected performance: **1000 games in seconds, not hours**, once fast mode is enabled and you avoid extra outputs.

---

## ⚙️ Advanced / Testing Commands

Legacy commands from previous versions:

---

## ✅ IN-PROCESS (FASTEST) — run 1000 games

Use this when you want maximal speed without starting the HTTP server. This runs the in-process simulator (`--fast-inproc`) and avoids network/thread overhead.

```bash
cd "/home/daniel-andrade-martins/Desktop/Desktop/Engenharia Informática/3º Ano/2º Semestre/Projeto em Engenharia Informática/Sueca/sueca_1.4"
source .venv/bin/activate

# Recommended minimal-env (no MQTT, no thinking delays)
SUECA_STATISTICS_FAST_MODE=1 \
SUECA_MQTT_EVENTS=false \
SUECA_BOT_THINK_TIME=0 \
SUECA_BOT_LOOP_SLEEP_MIN=0.0 \
SUECA_BOT_LOOP_SLEEP_MAX=0.0 \
SUECA_BOT_ERROR_SLEEP=0 \
SUECA_BOT_VERBOSE=false \
./.venv/bin/python statistic-analysis/data_gatherer.py \
  --matches 1000 \
  --fast-inproc \
  --no-game-files \
  --poll-interval 0.0

# Alternate (when using combinations file):
SUECA_STATISTICS_FAST_MODE=1 \
SUECA_MQTT_EVENTS=false \
SUECA_BOT_THINK_TIME=0 \
SUECA_BOT_LOOP_SLEEP_MIN=0.0 \
SUECA_BOT_LOOP_SLEEP_MAX=0.0 \
SUECA_BOT_ERROR_SLEEP=0 \
SUECA_BOT_VERBOSE=false \
./.venv/bin/python statistic-analysis/data_gatherer.py \
  --combinations-file statistic-analysis/combinations.example.json \
  --games-per-combination 1000 \
  --generation Gen1 \
  --output-dir statistic-analysis/batch_output \
  --no-game-files \
  --continue-on-error \
  --match-retries 3 \
  --fast-inproc \
  --poll-interval 0.0
```

Tip: wrap the command with `time` to measure total runtime, e.g.:

```bash
time SUECA_STATISTICS_FAST_MODE=1 SUECA_MQTT_EVENTS=false SUECA_BOT_THINK_TIME=0 \
  SUECA_BOT_LOOP_SLEEP_MIN=0.0 SUECA_BOT_LOOP_SLEEP_MAX=0.0 \
  ./.venv/bin/python statistic-analysis/data_gatherer.py --matches 1000 --fast-inproc --no-game-files --poll-interval 0.0
```

---

## 💾 Save Batch CSVs (summary + rounds)

To produce CSV tables (one summary CSV and one rounds CSV) for a fast in-process batch, use `--split-csv` and optionally `--no-game-files` to skip per-game JSON/CSV files and keep only the batch tables.

```bash
cd "/home/daniel-andrade-martins/Desktop/Desktop/Engenharia Informática/3º Ano/2º Semestre/Projeto em Engenharia Informática/Sueca/sueca_1.4"
source .venv/bin/activate

# Fast in-process run that writes batch CSVs into the output directory
SUECA_STATISTICS_FAST_MODE=1 SUECA_MQTT_EVENTS=false SUECA_BOT_THINK_TIME=0 \
  ./.venv/bin/python statistic-analysis/data_gatherer.py \
    --matches 1000 \
    --fast-inproc \
    --split-csv \
    --no-game-files \
    --output-dir statistic-analysis/batch_output_csv \
    --poll-interval 0.0

# After completion, batch CSVs will be at:
# statistic-analysis/batch_output_csv/tables/batch_summary.csv
# statistic-analysis/batch_output_csv/tables/batch_rounds.csv
```

## 🛠 Verify & Repair Batch CSVs

If you see missing `round_points`, `winner_team`, or the `team*_after` fields in `batch_rounds.csv`, run this quick repair script which infers the missing values from the next-round "before" columns and the final scores in `batch_summary.csv`.

Run from the workspace root:

```bash
source .venv/bin/activate
python3 - <<'PY'
import csv
from pathlib import Path
root=Path('statistic-analysis/batch_output_inproc_test/Gen1/tables')
rounds_f=root/'batch_rounds.csv'
summary_f=root/'batch_summary.csv'
print('Repairing', rounds_f, 'and', summary_f)
from collections import defaultdict
with open(summary_f,'r',encoding='utf-8') as f:
  summary=list(csv.DictReader(f))
final_scores={r['game_id']:(int(r.get('team1_score') or 0), int(r.get('team2_score') or 0)) for r in summary}
with open(rounds_f,'r',encoding='utf-8') as f:
  rows=list(csv.DictReader(f))
groups=defaultdict(list)
for r in rows: groups[r['game_number']].append(r)
for gnum,rs in groups.items():
  rs.sort(key=lambda x:int(x['round_number']))
  for i,r in enumerate(rs):
    tb_before=int(r.get('team1_before') or 0)
    t2_before=int(r.get('team2_before') or 0)
    if i+1<len(rs):
      nb=rs[i+1]
      tb_after=int(nb.get('team1_before') or 0)
      t2_after=int(nb.get('team2_before') or 0)
    else:
      tb_after,t2_after=final_scores.get(r['game_id'],(tb_before,t2_before))
    r['team1_after']=str(tb_after); r['team2_after']=str(t2_after)
    d1=tb_after-tb_before; d2=t2_after-t2_before
    if d1>d2: r['round_points']=str(d1); r['round_winner_team']='team1'
    elif d2>d1: r['round_points']=str(d2); r['round_winner_team']='team2'
    else: r['round_points']=str(max(d1,d2)); r['round_winner_team']='draw' if d1==d2 else ''
with open(rounds_f,'w',encoding='utf-8',newline='') as f:
  writer=csv.DictWriter(f, fieldnames=rows[0].keys())
  writer.writeheader(); writer.writerows(rows)
for r in summary:
  r['rounds_played']='10'
  t1=int(r.get('team1_score') or 0); t2=int(r.get('team2_score') or 0)
  if t1>t2: r['winner_team']='team1'; r['winner_label']='Team 1 (N/S)'
  elif t2>t1: r['winner_team']='team2'; r['winner_label']='Team 2 (E/W)'
  else: r['winner_team']='draw'; r['winner_label']='draw'
with open(summary_f,'w',encoding='utf-8',newline='') as f:
  writer=csv.DictWriter(f, fieldnames=summary[0].keys())
  writer.writeheader(); writer.writerows(summary)
print('Done')
PY

After running the repair script, view the files:

```bash
ls -l statistic-analysis/batch_output_inproc_test/Gen1/tables
head -n 20 statistic-analysis/batch_output_inproc_test/Gen1/tables/batch_rounds.csv
head -n 20 statistic-analysis/batch_output_inproc_test/Gen1/tables/batch_summary.csv
```

If you'd like, I can commit these repaired CSVs to the workspace or run a larger in-process batch (100/1000 games) and produce fresh CSVs. Which would you prefer?