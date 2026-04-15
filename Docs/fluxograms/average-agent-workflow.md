```mermaid
%%{init: {'flowchart': {'nodeSpacing': 20, 'rankSpacing': 25}}}%%
flowchart TD

A(Game Start) --> B[Join Game]
B --> C{Join Successful?}
C -->|No| D(End)
C -->|Yes| E[Set Player Name]

E --> F[Get Status]
F --> G{State None?}
G -->|Yes| H[Sleep 1s]
H --> F
G -->|No| I[Update State Tracker]

I --> J[Get Hand]
J --> K[Update My Hand]
K --> L{Current Phase?}

L -->|Cut Deck| M[Handle Cut Deck]
M -->N{Am I North?}
N -->|Yes|O[Choose Deck Cut]
O -->W[Send Cut Deck Index]
W -->X{Was Cut Successful?}
X -->|Yes|Y[Print Cut Success]
Y --> F
X -->|No|Z[Print Error]
Z -->L
N -->|No|L


L -->|Select Trump| P[Handle Select Trump]
P -->A1{Am I West?}
A1 --> |Yes|C1[Choose Trump Selection]
A1 --> |No|L
C1 --> D1[Select Trump]
D1 --> E1{Was Selection Successful?}
E1 --> |Yes| F1[Print Select Success]
F1 --> F
E1 --> |No| G1[Print Error]
G1 --> L



L -->|Playing| R[Handle Playing]
R --> H1{Is It My Turn & Do I Have Cards?}

H1 -->|Yes| K1["Call DecisionMaker\n(see diagram below)"]
H1 -->|No| L

I1 --> K1[Choose Card]
K1 --> L1{Is Card None?}
L1 -->|Yes|K1
L1 -->|No|N1[Convert To String]
N1 -->O1[Send Play Card]
O1 -->P1{Was Play Successful?}
P1 -->|Yes|Q1[Get Card Display]
Q1 -->R1[Print Agent Played X]
R1 -->F
P1 -->|No|T1[Print Error Message]
T1 -->R


L -->|Finished| T[Print Final Scores]
T --> S3(End)
L -->|Other| U[Sleep Random]

M --> F
P --> F
R --> F
U --> F
```
---
```mermaid
%%{init: {'flowchart': {'nodeSpacing': 25, 'rankSpacing': 30}}}%%
flowchart TD

A([Start Decision]) --> B{Hand Empty?}
B -->|Yes| R0([Return None])
B -->|No| C[Get Legal Plays]

C --> D{Only 1 Legal Play?}
D -->|Yes| R1([Return That Card])
D -->|No| E[Check Trick Position]

E --> F{Position in Trick?}

F -->|Lead| G[Lead Logic]
F -->|Middle| H[Middle Logic]
F -->|Last| I[Last Logic]

%% ================= LEAD =================
G --> G1{Round <= 4?}

G1 -->|Yes| G2[Try Play Non-Trump Ace]
G2 --> G3{Found Ace?}
G3 -->|Yes| END
G3 -->|No| G4[Continue Rules]

G1 -->|No| G4

G4 --> G5{Round >= 8?}
G5 -->|Yes| G6[Play Highest Card]
G5 -->|No| G7[Play Medium Non-Trump]

G7 --> G8{Non-Trumps Exist?}
G8 -->|Yes| END
G8 -->|No| G9[Play Lowest Trump]

G6 --> END
G9 --> END

%% ================= MIDDLE =================
H --> H1{Partner Winning?}

H1 -->|Yes| H2[Play Lowest Non-Trump]
H2 --> END

H1 -->|No| H3[Check Trick Points]

H3 --> H4{Points >= 10?}

H4 -->|No| H5[Play Lowest Card]
H5 --> END

H4 -->|Yes| H6[Try Lowest Winning Card]

H6 --> H7{Winning Card Exists?}

H7 -->|Yes| H8[Play Winning Card]
H7 -->|No| H9[Try Any Winning Card]

H9 --> H10{Winning Card Exists?}
H10 -->|Yes| H8
H10 -->|No| H5

H8 --> END

%% ================= LAST =================
I --> I1{Points >= 10?}

I1 -->|No| I2{Partner Winning?}
I2 -->|Yes| I3[Play Lowest Non-Trump]
I2 -->|No| I4[Play Lowest Card]

I3 --> END
I4 --> END

I1 -->|Yes| I5{Partner Winning?}

I5 -->|Yes| I6[Handle Scoring Cards]
I6 --> I7{Few Scoring Cards?}

I7 -->|Yes| I8[Play Highest Scoring Card]
I7 -->|No| I9[Play Mid-Value Scoring Card]

I8 --> END
I9 --> END

I5 -->|No| I10[Try Win Trick]

I10 --> I11{Winning Card Exists?}

I11 -->|Yes| I12[Play Winning Card]
I11 -->|No| I13[Play Lowest Non-Trump]

I12 --> END
I13 --> END

%% ================= END =================
END([Return Card])

R0 --> END
R1 --> END
```
---