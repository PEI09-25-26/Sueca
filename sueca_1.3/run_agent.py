#!/usr/bin/env python3
"""
Quick runner for testing WeakAgent

Usage:
    python run_agent.py          # Run one agent
    python run_agent.py AI_Bob   # Run agent with custom name
"""
import sys
from agent1 import WeakAgent


if __name__ == "__main__":
    # Get agent name from command line or use default
    agent_name = sys.argv[1] if len(sys.argv) > 1 else "WeakAI"
    
    print(f"Starting agent: {agent_name}")
    print("Make sure server is running on localhost:5000")
    print("Press Ctrl+C to stop\n")
    
    try:
        agent = WeakAgent(agent_name)
        agent.run()
    except KeyboardInterrupt:
        print("\n\nAgent stopped by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
