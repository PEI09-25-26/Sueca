# 🧪 Sueca Data Gatherer – Run 10000 Games

To run a batch of 1000 games using the optimized in-process simulator with accurate round-by-round points and simplified JSON output please use this command:

```
SUECA_STATISTICS_FAST_MODE=1 SUECA_MQTT_EVENTS=false SUECA_BOT_THINK_TIME=0   ./.venv/bin/python statistic-analysis/data_gatherer.py     --matches 10000     --fast-inproc     --split-csv     --no-game-files     --output-dir statistic-analysis/batch_output_10000     --poll-interval 0.0 --combinations-file ./statistic-analysis/combinations.example.json
```
