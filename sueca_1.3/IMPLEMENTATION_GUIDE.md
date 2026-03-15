# WeakAgent Implementation Guide

## 🎯 Learning Order

Complete the classes in this order:

### 1. **CardAnalyzer** (DONE) 
- **Why first?** No dependencies, pure logic functions
- **File:** `card_analyzer.py`
- **Key concepts:** Card strength, legal plays, winning calculations
- **Time:** ~30-45 minutes

### 2. **GameStateTracker** (DONE)
- **Why second?** Uses only CardAnalyzer, builds game knowledge
- **File:** `game_state_tracker.py`
- **Key concepts:** State management, team tracking, card inference
- **Time:** ~45-60 minutes

### 3. **DecisionMaker** (DONE)
- **Why third?** Uses both previous classes to make decisions
- **File:** `decision_maker.py`
- **Key concepts:** Heuristics, strategy, card selection
- **Time:** ~30-45 minutes

### 4. **WeakAgent** (DONE)
- **Why last?** Orchestrates everything, handles server communication
- **File:** `agent1.py`
- **Key concepts:** Main loop, server API, automation
- **Time:** ~20-30 minutes

### 5. **Break** (IN PROGRESS) ⭐
- **Why do it?** I'm tired man I need some coffee or something T-T
- **Key concepts:** Food, coffee, break
- **Time:** From when I hit push to when you respond with your own changes :D

---

## 🧪 Testing Strategy

### Test as you go:
```bash
# After completing CardAnalyzer:
python test_weak_agent.py

# It will show which tests pass/fail
# Fix errors before moving to next class
```

### Manual testing with real server:

1. **Start the server:**
```bash
python server.py
```

2. **In another terminal, start human clients:**
```bash
python client.py  # Start 3 human players
```

3. **In a third terminal, test your agent:**
```bash
python -c "from agent1 import WeakAgent; agent = WeakAgent('AI1'); agent.run()"
```

---

## 📚 Implementation Tips

### CardAnalyzer Tips:
- **Card IDs:** 0-9 = ♣, 10-19 = ♦, 20-29 = ♥, 30-39 = ♠
- **Within suit:** index%10 gives rank (0=2, 1=3, ..., 8=7, 9=A)
- **Use CardMapper:** Already handles conversions
- **Tuple comparison:** `(2, 5) > (1, 9)` is `True` (compares left-to-right)

### GameStateTracker Tips:
- **Teams:** North-South vs East-West
- **Void detection:** If player doesn't follow suit → they're void
- **Update order:** Always update state before making decisions
- **Remaining cards:** Start with set(range(40)), remove as played

### DecisionMaker Tips:
- **Partner winning = play low** (most important rule!)
- **High-value trick = try to win** (if no partner winning)
- **Lead suit must be followed** (use get_legal_plays)
- **Trump is powerful** (category 2 beats category 1 and 0)

### WeakAgent Tips:
- **Main loop:** Get status → Update state → Handle phase → Sleep
- **Error handling:** Always check if methods return None
- **Server delays:** Use sleep() to avoid hammering server
- **Print messages:** Help debug what agent is doing

---

## 🎮 How to Test Full Game

1. **Start server:**
```bash
cd sueca_1.3
python server.py
```

2. **Start 4 agents** (in separate terminals):
```bash
python -c "from agent1 import WeakAgent; WeakAgent('AI_North').run()"
python -c "from agent1 import WeakAgent; WeakAgent('AI_East').run()"
python -c "from agent1 import WeakAgent; WeakAgent('AI_South').run()"
python -c "from agent1 import WeakAgent; WeakAgent('AI_West').run()"
```

Watch them play!

---

## 🐛 Common Errors

### "CardMapper has no attribute X"
- Make sure you're importing correctly: `from card_mapper import CardMapper`

### "GameStateTracker object has no attribute X"
- Did you initialize all attributes in `__init__`?
- Check you called `super().__init__()` in subclasses

### "None is not iterable"
- Check if methods might return None before using them

### "Index out of range"
- Verify card_id is 0-39
- Check if lists are empty before accessing

---

## ✅ Success Criteria

### CardAnalyzer Done When:
- ✓ Can determine card strength correctly
- ✓ Identifies legal plays (follow suit rule)
- ✓ Finds winning cards
- ✓ All test_card_analyzer() tests pass

### GameStateTracker Done When:
- ✓ Correctly identifies team and partner
- ✓ Tracks remaining cards
- ✓ Determines trick winner
- ✓ All test_game_state_tracker() tests pass

### DecisionMaker Done When:
- ✓ Makes valid card choices
- ✓ Doesn't waste cards when partner winning
- ✓ Tries to win high-value tricks
- ✓ All test_decision_maker() tests pass

### WeakAgent Done When:
- ✓ Joins game automatically
- ✓ Plays cards in correct order
- ✓ Completes full game without errors
- ✓ Can run 4 agents simultaneously

---

## 🚀 Next Steps After WeakAgent

Want to make it stronger? Try:

1. **Better trump selection:**
   - Analyze both top and bottom cards
   - Choose suit you have more cards in

2. **Card counting:**
   - Track which high cards are still out
   - Adjust strategy based on remaining cards

3. **Smarter leading:**
   - Lead suit where opponents might be void
   - Lead high cards when you have long suit

4. **Monte Carlo simulation:**
   - Simulate possible opponent hands
   - Choose card with best expected outcome

5. **Machine learning:**
   - Learn from game results
   - Optimize heuristic weights

---

## 📖 Useful References

- **Server API:** See `server.py` endpoints
- **Client methods:** Check `client.py` for available functions
- **Card mapping:** Review `card_mapper.py` for conversions
- **Sueca rules:** Portuguese card game, 4 players, follow suit, trump beats all

---

Good luck! Start with CardAnalyzer and work your way up! 🎴
