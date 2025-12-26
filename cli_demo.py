from agent.agent import travel_agent
from memory.mongo_store import (
    start_conversation,
    get_context,
    save_turn
)

convo_id = start_conversation()

print("\n🧳 Travel Planning Agent (Mongo + Ollama)")
print("Type 'exit' to quit\n")

while True:
    msg = input("You: ")
    if msg.lower() == "exit":
        break

    context = get_context(convo_id)

    response = travel_agent(msg, context)

    save_turn(
        convo_id,
        msg,
        response.get("message"),
        response.get("tool_used")
    )

    print("\nAgent:", response["message"])

    if "result" in response:
        for item in response["result"]:
            print("-", item)

    print()
