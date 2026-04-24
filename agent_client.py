from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from openai.types.responses.response_input_param import McpApprovalResponse

project_endpoint = "https://ai-103-demo-res.services.ai.azure.com/api/projects/ai-103-demo-proj"
agent_name = "product-expert-agent"

credential = DefaultAzureCredential()

project_client = AIProjectClient(
    credential=credential,
    endpoint=project_endpoint
)

# Get the OpenAI client
openai_client = project_client.get_openai_client()

# Get the agent
agent = project_client.agents.get(agent_name=agent_name)
print(f"Connected to agent: {agent.name} (id: {agent.id})\n")

# Create a new conversation
conversation = openai_client.conversations.create(items=[])
print(f"Created conversation (id: {conversation.id})\n")

def send_message_to_agent(user_message):
    print("Agent: ", end="", flush=True)

    # Add user message to the conversation
    openai_client.conversations.items.create(
        conversation_id=conversation.id,
        items=[{"type": "message", "role": "user", "content": user_message}],
    )

    # Create a response using the agent
    response = openai_client.responses.create(
        conversation=conversation.id,
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
        input=""
    )

    # Check if the response output contains an MCP approval request
    approval_request = None
    if hasattr(response, 'output') and response.output:
        for item in response.output:
            if hasattr(item, 'type') and item.type == 'mcp_approval_request':
                approval_request = item
                break

    # Handle approval request if present
    if approval_request:
        print(f"[Approval required for: {approval_request.name}]\n")
        print(f"Server: {approval_request.server_label}")

        # Parse and display the arguments (optional, for transparency)
        import json
        try:
            args = json.loads(approval_request.arguments)
            print(f"Arguments: {json.dumps(args, indent=2)}\n")
        except:
            print(f"Arguments: {approval_request.arguments}\n")

        # Prompt user for approval
        approval_input = input("Approve this action? (yes/no): ").strip().lower()

        if approval_input == 'yes':
            # Create approval response item
            approval_response = McpApprovalResponse(
                        type="mcp_approval_response",
                        approve=True,
                        approval_request_id=item.id,
                    )
        else:
            print("Action denied.\n")
            # Create denial response item
            approval_response = McpApprovalResponse(
                        type="mcp_approval_response",
                        approve=False,
                        approval_request_id=item.id,
                    )

        # Add the approval response to the conversation
        openai_client.conversations.items.create(
            conversation_id=conversation.id,
            items=[approval_response]
        )

        # Get the actual response after approval/denial
        response = openai_client.responses.create(
            conversation=conversation.id,
            extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
            input=""
        )

    # Extract the response text
    if response and response.output_text:
        print(f"{response.output_text}\n")

        # Check for citations if available
        if hasattr(response, 'citations') and response.citations:
            print("\nSources:")
            for citation in response.citations:
                print(f" - {citation.content if hasattr(citation, 'content') else 'Knowledge Base'}")
        return response.output_text
    else:
        print("No response received.\n")
        return None

def main():
    print("Contoso Product Expert Agent")
    print("Ask questions about our outdoor and camping products.")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() == 'quit':
            print("\nEnding conversation...")
            break

        # Send message and get response
        send_message_to_agent(user_input)

    print("\nConversation ended.")


if __name__ == "__main__":
    main()
