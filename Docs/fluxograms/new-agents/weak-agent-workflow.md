# MAIN FLUXOGRAM FOR THE OVERALL WORKFLOW OF THE WEAK AGENT
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


%% Decision Maker output (FROM second diagram conceptually)
K1 --> L1{Card Returned?}

L1 -->|None| K1
L1 -->|Valid Card| N1[Convert To String]

N1 --> O1[Send Play Card]
O1 --> P1{Was Play Successful?}
P1 -->|Yes| Q1[Get Card Display]
Q1 --> R1[Print Agent Played X]
R1 --> F
P1 -->|No| T1[Print Error Message]
T1 --> R

L -->|Finished| T[Print Final Scores]
T --> S3(End)
L -->|Other| U[Sleep Random]

M --> F
P --> F
R --> F
U --> F
```
---
## SECONDARY FLUXOGRAM WITH THE DETAILS OF CARD PICKING DECISION MAKING FOR THIS MODEL
```mermaid
%%{init: {'flowchart': {'nodeSpacing': 25, 'rankSpacing': 30}}}%%
flowchart TD

A([Start Decision]) --> B{Hand Empty?}
B -->|Yes| R0([Return None])
B -->|No| C[Get Legal Plays]

C --> D{Only 1 Legal Play?}
D -->|Yes| R1([Return That Card])
D -->|No| E[Cards Played in Trick]

E --> F{Position?}

F -->|Lead| G[Lead Logic]
F -->|Middle| H[Random Choice]
F -->|Last| I[Last Logic]

%% ---------------- LEAD ----------------
G --> G0[Split Trumps / Non-Trumps]

G0 --> G00[Detect Danger Suits]
G00 --> G01[Filter Safe Non-Trumps]
G01 --> G02[Prefer Partner-Safe Cards]

G02 --> G1{Round <= 4?}
G1 -->|Yes| G1A[Play Safe Ace if Exists]

G1 --> G3{Round >= 8?}
G3 -->|Yes| G4[Play High Point Card]

G3 -->|No| G5[Check Special Cases]

G5 --> G6{7 & Ace Gone?}
G6 -->|Yes| G7[Play 7]

G6 -->|No| G8[Play Safe Ace if Exists]

G8 --> G9[Play Medium / Zero-Point Card]

G4 --> END
G7 --> END
G9 --> END

G02 --> G10{No Safe Cards?}
G10 -->|Danger Non-Trumps| G11[Play Lowest Danger Card]
G10 -->|Else| G12[Play Lowest Trump]

G11 --> END
G12 --> END

%% ---------------- MIDDLE ----------------
H --> H1[Play Random Card]
H1 --> END

%% ---------------- LAST ----------------
I --> I1{Partner Winning?}

I1 -->|Yes| I2[Play Random Card]

I1 -->|No| I3[Get Trick Points]

I3 --> I4{Points < 10?}

I4 -->|Yes| I5[Try Lowest Winning Card]
I5 --> I6{Exists?}
I6 -->|Yes| I7[Play Winning Card]
I6 -->|No| I8[Play Lowest Card]

I4 -->|No| I9[Play Random Card]

I2 --> END
I7 --> END
I8 --> END
I9 --> END

%% ---------------- END ----------------
END([Return Card])
R0 --> END
R1 --> END
```
--- 
