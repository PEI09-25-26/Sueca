# MAIN FLUXOGRAM FOR THE OVERALL WORKFLOW OF THE RANDOM AGENT
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
flowchart TD

subgraph DECISION_MAKER_RANDOM [Random Decision Maker]

DC_START([Choose Card Called])

DC_1{Hand Empty?}
DC_1 -->|Yes| DC_NULL([Return None])
DC_1 -->|No| DC_2[Get Legal Plays]

DC_2 --> DC_3[Random Choice]

DC_3 --> DC_END([Return Selected Card])
```
---