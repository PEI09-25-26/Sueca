import csv
import sys
from pathlib import Path
import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).parent
DEFAULT_DATA_PATH = SCRIPT_DIR / "batch_output_10000/weak_weak_weak_weak/tables/batch_summary.csv"

def main():
    # Allow passing a custom path to the summary CSV as an argument
    if len(sys.argv) > 1:
        data_path = Path(sys.argv[1])
    else:
        data_path = DEFAULT_DATA_PATH

    if not data_path.exists():
        print(f"Error: File not found at {data_path}")
        print("Usage: python statistic-analysis/extract_winners.py [path_to_batch_summary.csv]")
        return

    team1_counter = 0
    team2_counter = 0
    draw_counter = 0

    with open(data_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            winner = row.get("winner_team")
            if winner == "team1":
                team1_counter += 1
            elif winner == "team2":
                team2_counter += 1
            else:
                draw_counter += 1

    print("Team 1 (N/S) wins:", team1_counter)
    print("Team 2 (E/W) wins:", team2_counter)
    print("Draws:", draw_counter)

    fig, ax = plt.subplots()
    ax.pie([team2_counter, team1_counter, draw_counter], labels=['Team 2 (Weak)', 'Team 1 (Weak)', 'Draws'], autopct='%1.1f%%', textprops={'fontsize': 14})
    ax.set_title("Team Wins", fontsize=16)

    # Save the graph inside the batch output directory (parent of tables/)
    graph_path = data_path.parent.parent / "graph.png"
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(graph_path)
    print(f"Graph saved to: {graph_path}")


if __name__ == "__main__":
    main()