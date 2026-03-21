"""
Quick runner for the WeakAgent
"""
import sys
from weakAgent import WeakAgent


if __name__ == "__main__":
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
