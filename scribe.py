# Import timestamp tools
from datetime import datetime

# Import Python client for local Ollama models
import ollama


# Startup banner
print("=== Scribe v0.2 ===")


# Ask user for metadata about the lab
lab_name = input("Lab name: ")
objective = input("Objective: ")


# Instructions
print("\nPaste command output. Press Enter twice when done.\n")


# Empty list to store pasted terminal output
lines = []


# Collect terminal output line by line
while True:
    line = input()

    # Stop collecting when blank line entered
    if line == "":
        break

    # Add line to list
    lines.append(line)


# Join all captured lines into one string
output = "\n".join(lines)


# Create timestamp
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")


# Prompt sent to local AI model
# This tells the model HOW to analyze output
prompt = f"""
You are a technical lab assistant.

Analyze this output.

Respond ONLY using:

Observation:
Lesson:
Suggested Next Command:
Interview Bullet:
GitHub Tags:

Be concise.
Assume the user is studying infrastructure/security.

Output:

{output}
"""


# Send prompt to local Ollama model
response = ollama.chat(

    # Choose local model
    model="qwen2.5:14b",

    # User message sent to model
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ]
)


# Extract only model response text
analysis = response["message"]["content"]


# Build markdown report
markdown = (
f"# {lab_name}\n\n"
f"**Date:** {timestamp}\n\n"
f"## Objective\n"
f"{objective}\n\n"

f"## Raw Output\n"
f"```text\n{output}\n```\n\n"

f"## AI Analysis\n"
f"{analysis}\n"
)

# Create filename from lab name
filename = f"output/{lab_name.replace(' ','_')}.md"


# Save markdown to output folder
with open(filename, "w", encoding="utf-8") as f:
    f.write(markdown)


# Confirm save
print(f"\nSaved: {filename}")