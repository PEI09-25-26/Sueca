# 🧪 Sueca Data Gatherer – Run 1000 Games

To run a batch of 1000 games using the optimized in-process simulator with accurate round-by-round points and simplified JSON output:

## 🚀 Quick Start (In-Process Mode)

This is the fastest method and does not require starting a separate engine server.

```bash
# 1. Navigate to the project root
cd "/home/daniel-andrade-martins/Desktop/Desktop/Engenharia Informática/3º Ano/2º Semestre/Projeto em Engenharia Informática/Sueca/sueca_1.4"

# 2. Activate the virtual environment
source .venv/bin/activate

# 3. Run the 1000 games batch
```

SUECA_STATISTICS_FAST_MODE=1 SUECA_MQTT_EVENTS=false SUECA_BOT_THINK_TIME=0 \
  ../../venv/bin/python statistic-analysis/data_gatherer.py \
    --matches 1000 \
    --fast-inproc \
    --split-csv \
    --no-game-files \
    --output-dir statistic-analysis/batch_output_1000 \
    --poll-interval 0.0

```

```

SUECA_STATISTICS_FAST_MODE=1 SUECA_MQTT_EVENTS=false SUECA_BOT_THINK_TIME=0   ../../venv/bin/python statistic-analysis/data_gatherer.py     --matches 1000     --fast-inproc     --split-csv     --no-game-files     --output-dir statistic-analysis/batch_output_1000     --poll-interval 0.0 --combinations-file ./statistic-analysis/combinations.example.json

```

## 📂 Output Files

After completion, the results will be available in:
- **Summary Table**: `statistic-analysis/batch_output_1000/Gen1/tables/batch_summary.csv`
- **Rounds Table**: `statistic-analysis/batch_output_1000/Gen1/tables/batch_rounds.csv`

The `batch_rounds.csv` file contains a `round_actions` JSON column with simplified state snapshots (no player names/choices, flattened card lists) optimized for debugging and ML training.

## ⚙️ Environment Variables Explained

- `SUECA_STATISTICS_FAST_MODE=1`: Enables high-speed simulation logic.
- `SUECA_MQTT_EVENTS=false`: Disables MQTT overhead.
- `SUECA_BOT_THINK_TIME=0`: Removes artificial delays in bot decision-making.