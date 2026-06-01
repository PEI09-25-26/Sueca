# Important Information

### Data gathering proccess:
- 10.000 games were played, rotating the starting player in each game (S->E->N->W->S->...)
- The data was gathered in a different game server than the application is ran in, using the same logic as the live server
- The simulations always use two teams of bots where each of the players is using the same difficulty, i.e., each team will always consist of two players with the same set of heuristics which make up their decision making logic.
- The file ran to generate and gather information from these games was the data_gatherer.py and the file that creates the graph was the extract_winners.py

### Small inconsistencies present:
- The results of games between two teams of equal bot difficulty always *slightly* favours Team 2, likely due to trump setting rules

### Other pointers:
- In the future, the data will be cleaned and formatted in order to provide a faithful and diverse dataset to be used later in Machine Learning models for another bot we will be calling the "expert" difficulty.
- Future versions of the data gathering proccess might make the general structure different from what is mentioned in this file.
