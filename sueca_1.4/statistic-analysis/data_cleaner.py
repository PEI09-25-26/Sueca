import csv
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def clean_cards_played(df):

Tk().withdraw()
DATA_PATH = askopenfilename(filetypes=[("Ficheiros CSV", "*.csv"), ("Todos os ficheiros", "*.*")])

#Read uncleaned data
df = pd.read_csv(DATA_PATH)

df_v1 = df.drop(columns=['game_id', 'cards_played_count'])

df_v1['round_winner_team'] = df_v1['round_winner_team'].replace({'draw': 0, 'team1': 1, 'team2': 2})



#Save cleaned data
CLEANED_DATA_PATH = DATA_PATH.replace('.csv', '_cleaned.csv')
df_v1.to_csv(CLEANED_DATA_PATH, index=False)

