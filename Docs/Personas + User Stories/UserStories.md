# User Stories:
### Changing Profile information
    Priority: Medium
    Estimate: 2 Story Points

    As a user,
    I want to be able to change the username and the profile picture,
    so that I can better express myself, be more easily recognized by my friends in online lobbies/tables and costumize my profile to my likings.

    Given that I have the profile menu open,
    When I open the click on my username and/or picture,
    Then I should be able to change my username and profile picture.

### Match History
    Priority: Low
    Estimate: 5 Story Points

    As a user,
    I want to be able to see the statistics related to the matches I have played in the past in my profile,
    so that I can see my history and performance/proficiency I have at playing Sueca when using the app.

    Given that I have played at least more than one game using the app,
    When I am browsing my profile,
    Then I should be able to see the statistics related to the number of wins, win rate, highest score and the total number of games I have played while using the app while checking my profile.

### Use AI Players in a Physical Sueca Game
    Priority: High
    Estimate: 20 Story Points

    As a user,
    I want to integrate AI players into a real, physical Sueca match,
    so that I can enjoy a full game even when there aren’t enough human players and maintain fair play through AI arbitration.

    Given that I’m setting up a physical Sueca game with real cards,
    When I choose to activate AI players in the app and show their dealt cards using a camera or manual input,
    Then the AI players should be able to make decisions and play according to the standard Sueca rules.

### Use AI Players in an Online Sueca game
    Priority: High
    Estimate: 12 Story Points

    As a user,
    I want to integrate AI players into a online game of Sueca,
    so that I can enjoy a full game even when there aren't enough human players in the online table to start a Sueca match.

    Given that I'm hosting an online table in the app,
    When I choose to add an AI player to the table,
    Then an AI player should join the game and be able to make decisions and play according to the standard Sueca rules.
    
### Costumize the skill level of the AI player
    Priority: Medium
    Estimate: 8 Story Points

    As a user,
    I want to be able to costumize the skill level of the AI players I use in my games,
    so that I can better adapt it to the context and way of playing being used in my physical or online table.

    Given that I am hosting a Sueca game, wether physical or online,
    When I choose the option to add an AI player,
    Then I should be able to choose the skill level of the AI player so it better fits what I want.

### Hosting and Joining an online table
    Priority: High
    Estimate: 8 Story Points

    As a user,
    I want to be able to host or join an online table,
    so that I can play a game of Sueca online.

    Given that I have the online lobby menu open and I have a stable internet connection,
    When I select the option to host or join an online table,
    Then I should be able to create or join that table and play the game when the me or the host starts it.

### Online play in a Physical Sueca game
    Priority: Medium
    Estimate: 10 Story Points

    As a user,
    I want to be able to join a physical game of Sueca,
    so that I can play it while not being present there.

    Given that a physical game of Sueca is being held and shared using the online table system,
    When I join that table and the host starts the game,
    Then the card-detection AI should be able to properly identify my cards at the start of each round and I should be able to see the table, as well as select the card I want to play when my turn comes.

### Hosting and Joining a Tournament
    Priority: Medium
    Estimate: 12 Story Points

    As a user,
    I want to be able to host or join a tournament,
    so that people can play Sueca in an organized bracket, wether for a prize or just casually.

    Given that I am in the menu related to the tournaments,
    When I select the options to host or join a tournament,
    Then I should see the different options related to the tournament creation proccess or, in case of wanting to join one instead, the list of available tournaments.

### Filling the missing player slots with AI players in a Tournament
    Priority: Medium
    Estimate: 5 Story Points

    As a user,
    I want to be able to fill the missing player slots in my tournament bracket with AI players,
    so that I can complete the bracket without leaving anyone out, making for a better experience for everyone involved.

    Given that I am hosting a Sueca tournament using the app,
    When the bracket is not completely filled with real players by the time of the event, 
    Then I should be able to add AI players to any given table while browsing the bracket.

### Obtaining real-time information of the Tournament
    Priority: Low
    Estimate: 5 Story Points

    As a user,
    I want to be able obtain real-time information of a Sueca tournament,
    so that I can follow the results of each game better.

    Given that I am currently hosting, participating or even just following an ongoing tournament,
    When I browse the bracket and details of the tournament,
    Then I should be able to see real-time updates of information and scores in the bracket.

### Automatic Rule Enforcement / Arbitration
    Priority: High
    Estimate: 8 Story Points

    As a user,
    I want the app to automatically validate played cards and enforce Sueca rules,
    so that mistakes or cheating are prevented and the game flows correctly.

    Given that a round is ongoing,
    When a player attempts to play a card,
    Then the app should confirm it is a legal move and reject it if it violates the game rules.

### Card Detection Using Camera
    Priority: High
    Estimate: 20 Story Points

    As a user,
    I want the app to detect the cards on the table or in my hand using the camera,
    so that I don’t have to input cards manually and the game can be played fluidly in a physical environment.

    Given that I show my cards to the camera,
    When the system processes the image,
    Then it should identify the rank and suit of each card accurately.

### Automatic Round Tracking
    Priority: High
    Estimate: 8 Story Points

    As a user,
    I want the app to automatically track which player won each trick,
    so that the score and game progression are always correct.

    Given that a trick has just finished,
    When all four cards have been played,
    Then the app should identify the winner and update the turn order automatically.

### Synchronization of Physical–Remote Tables

    Priority: High
    Estimate: 10 Story Points

    As a remote user in a physical game,
    I want the app to synchronize the detected cards and table state in real-time,
    so that I can follow and play the game as if I were physically present.

    Given that a card is detected on the physical table,
    When the state updates,
    Then all remote players should see the change instantly.

### Public Display Mode

    Priority: Medium
    Estimate: 5 Story Points

    As a tournament organizer or spectator,
    I want the app to provide a public display mode,
    so that players and viewers can see the live status of the table without interacting with the device.

    Given that a table or tournament is ongoing,
    When I enable public display mode,
    Then the app should show the game state, scores and next plays in a clean visual layout.

### Team Setup for Sueca

    Priority: Medium
    Estimate: 3 Story Points

    As a user,
    I want to assign players to fixed teams,
    so that Sueca is played with the proper team composition.

    Given that I am setting up a table,
    When I add players or bots,
    Then I should be able to assign them to team A or team B.