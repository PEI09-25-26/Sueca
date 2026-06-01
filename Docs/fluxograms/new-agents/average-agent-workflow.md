# MAIN FLUXOGRAM FOR THE OVERALL WORKFLOW OF THE AVERAGE AGENT
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
F -->|Middle| H[Middle Logic]
F -->|Last| I[Last Logic]

%% ================= LEAD =================
G --> G0[Split Trumps / Non-Trumps]
G0 --> G00[Detect Danger Suits]
G00 --> G01[Safe Non-Trumps]
G01 --> G02[Partner-Safe Preference]

G02 --> G1{Round <= 4?}
G1 -->|Yes| G1A[Play Safe Ace]

G1 --> G3{Round >= 8?}
G3 -->|Yes| G4[Play High Point Card]

G3 -->|No| G5[Special Rules]

G5 --> G6{7 & Ace Gone?}
G6 -->|Yes| G7[Play 7]

G6 -->|No| G8[Play Safe Ace or Medium Card]

G4 --> END
G7 --> END
G8 --> END

G02 --> G10{No Safe Cards?}
G10 -->|Danger Non-Trumps| G11[Lowest Danger Card]
G10 -->|Else| G12[Lowest Trump]

G11 --> END
G12 --> END

%% ================= MIDDLE =================
H --> H1{Partner Winning?}

H1 -->|Yes| H2{Non-Trumps Available?}
H2 -->|Yes| H3[Play Lowest Non-Trump]
H2 -->|No| H4[Play Lowest Card]

H1 -->|No| H5[Check Trick Points]

H5 --> H6{Points >= 10?}

H6 -->|No| H7[Play Lowest Card]

H6 -->|Yes| H8{Non-Trumps Available?}

H8 -->|Yes| H9[Try Lowest Winning Non-Trump]
H9 --> H10{Exists?}
H10 -->|Yes| H11[Play Winning Card]

H10 -->|No| H12[Try Any Winning Card]
H12 --> H13{Exists?}
H13 -->|Yes| H11
H13 -->|No| H7

H8 -->|No| H14[Try Any Winning Card]
H14 --> H13

H3 --> END
H4 --> END
H7 --> END
H11 --> END

%% ================= LAST =================
I --> I0[Split Non-Trumps / Pool]

I0 --> I1{Partner Winning?}

%% ---- Partner Winning ----
I1 -->|Yes| I2{Points < 10?}

I2 -->|Yes| I3[Play Lowest Zero-Point Non-Trump]
I3 --> I3A{Exists?}
I3A -->|Yes| END
I3A -->|No| I4[Play Lowest Card]

I2 -->|No| I5[Play High Point Non-Trump]
I5 --> I5A{Exists?}
I5A -->|Yes| END
I5A -->|No| I4

%% ---- Partner Losing ----
I1 -->|No| I6{Points >= 10?}

I6 -->|Yes| I7[Try Lowest Winning Card]
I7 --> I8{Exists?}

I8 -->|Yes| I9{Is A or 7?}

I9 -->|Yes| I10[Try Non-Key Winning Card]
I10 --> I11{Exists?}
I11 -->|Yes| I12[Play That Card]
I11 -->|No| I13[Play Winning Card]

I9 -->|No| I13

I8 -->|No| I14[Play Lowest Zero Card]
I14 --> I14A{Exists?}
I14A -->|Yes| END
I14A -->|No| I4

%% ---- Low Point Trick ----
I6 -->|No| I15[Play Lowest Zero Card]
I15 --> I15A{Exists?}

I15A -->|Yes| END
I15A -->|No| I16[Try Winning Card]

I16 --> I17{Exists?}

I17 -->|Yes| I18{Is A or 7?}

I18 -->|Yes| I19[Try Non-Key Zero Winning Card]
I19 --> I20{Exists?}
I20 -->|Yes| I12
I20 -->|No| I13

I18 -->|No| I13

%% fallback
I17 -->|No| I4

I4 --> END
I12 --> END
I13 --> END

%% ================= END =================
END([Return Card])
R0 --> END
R1 --> END
```
---
