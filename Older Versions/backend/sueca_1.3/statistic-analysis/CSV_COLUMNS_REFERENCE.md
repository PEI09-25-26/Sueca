# CSV Columns Reference

## batch_summary.csv

### Summary of each completed game.

| Column | Type | Description |
|--------|------|-------------|
| `game_number` | integer | Sequential game ID (1 to N) within each combination/generation |
| `game_id` | string | Unique server-assigned game identifier |
| `match_number` | integer | Server-side match index from history (usually `1` for this workflow; not game length) |
| `rounds_played` | integer | Number of rounds actually played in the game (typically `10` in your current ruleset) |
| `winner_team` | string | Winning team: `team1` (North/South) or `team2` (East/West) |
| `winner_label` | string | Human-readable winner: "Team 1 (N/S)" or "Team 2 (E/W)" |
| `team1_score` | integer | Final points scored by Team 1 (North/South) |
| `team2_score` | integer | Final points scored by Team 2 (East/West) |
| `trump_card` | integer | Rank of the trump card (10-39) |
| `trump_suit` | string | Trump suit: `♥` (Hearts), `♦` (Diamonds), `♠` (Spades), `♣` (Clubs) |
| `phase` | string | Game state at end (always "finished" for complete games) |
| `finished_at` | datetime | Timestamp when game completed (ISO 8601 format with timezone) |

### Usage notes for ML:

- **Game outcome**: Use `winner_team` or derive from score difference
- **Game length**: Use `rounds_played` (do not use `match_number` for this)
- **Card value**: Trump card rank (`trump_card`) is useful for feature engineering
- **Data quality**: If `trump_card` is blank/empty, that record may be unreliable; consider filtering

---

## batch_rounds.csv

### Detailed round-by-round statistics.

| Column | Type | Description |
|--------|------|-------------|
| `game_number` | integer | Sequential game ID |
| `game_id` | string | Unique game identifier |
| `round_number` | integer | Hand/round within the game (1-10) |
| `round_points` | integer | Points awarded in this round to the winning team of that round |
| `round_winner_team` | string | Which team won this specific round: `team1` or `team2` |
| `team1_before` | integer | Team 1's cumulative score **before** this round |
| `team2_before` | integer | Team 2's cumulative score **before** this round |
| `team1_after` | integer | Team 1's cumulative score **after** this round |
| `team2_after` | integer | Team 2's cumulative score **after** this round |
| `cards_played_count` | integer | Number of cards played in this round (always 4 in Sueca) |
| `cards_played` | string | Compact representation of cards played: `player_name:position:card_rank` separated by `\|` |

### Usage notes for ML:

- **Round progression**: Track score delta (`team_after - team_before`) to see which team is winning
- **Round dominance**: High `round_points` in early rounds may predict eventual winner
- **Card sequence**: `cards_played` is parseable but complex; mainly for detailed analysis

---

## File organisation

```
batch_output/
├── random-random-random-random/          (combination label with difficulty distribution)
│   ├── tables/
│   │   ├── batch_summary.csv              (one row per game)
│   │   └── batch_rounds.csv               (multiple rows per game, one per round)
│   ├── manifests/
│   │   └── batch_manifest.json            (list of games: IDs, status, errors)
│   └── metadata/
│       └── run_config.json                (command args used for this run)
├── all_combinations_manifest.json         (optional: aggregated metadata)
└── README.md                              (this folder structure)
```

---

## Tips

1. **Start with `batch_summary.csv`**: One row = one complete game. Simpler for initial ML.
2. **Add `batch_rounds.csv` later**: If you want to predict round-by-round outcomes or understand mid-game dynamics.
3. **Filter bad rows**: Remove any rows where `trump_card` is empty or `team1_score + team2_score == 0`.
4. **Feature engineering ideas**:
   - `trump_suit` → one-hot encode to 4 binary features
   - `trump_card` → normalize to [10-39] range
   - `rounds_played` → proxy for game length
   - Score difference: `team1_score - team2_score` → target for regression
