import csv
from pathlib import Path
import matplotlib.pyplot as plt


# Path relative to this script's directory
SCRIPT_DIR = Path(__file__).parent
DATA_PATH = SCRIPT_DIR / "batch_output_10000/smart_average_smart_average/tables/batch_summary.csv"

def main():
    if not DATA_PATH.exists():
        print(f"Error: File not found at {DATA_PATH}")
        return

    team1_counter = 0
    team2_counter = 0
    draw_counter = 0

    with open(DATA_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            winner = row.get("winner_team")
            if winner == "team1":
                team1_counter += 1
            elif winner == "team2":
                team2_counter += 1
            else:
                draw_counter += 1

    print("Team1 wins:", team1_counter)
    print("Team2 wins:", team2_counter)
    print("Draws:", draw_counter)

    fig, ax = plt.subplots()
    ax.pie([team2_counter, team1_counter, draw_counter], labels=['average', 'Smart', 'Draws'], textprops={'fontsize': 14})
    ax.set_title("Team Wins", fontsize=16)

    plt.savefig(SCRIPT_DIR / "batch_output_10000/smart_average_smart_average/graph.png")

    

if __name__ == "__main__":
    main()