# Import timestamp tools
from datetime import datetime

# Import tools for file paths
from pathlib import Path

# Import Python client for local Ollama models
import ollama


# -----------------------------
# Scribe Configuration
# -----------------------------

# Version label
VERSION = "v0.4"

# Local Ollama model to use
MODEL = "qwen2.5:14b"

# Anchor all paths to the directory this script lives in
# Prevents breakage when running from a different working directory
BASE_DIR = Path(__file__).parent.resolve()

# Output folder for generated lab notes (relative to script location)
OUTPUT_DIR = BASE_DIR / "output"

# README file to update with lab index (relative to script location)
README_FILE = BASE_DIR / "README.md"


# -----------------------------
# Helper Functions
# -----------------------------

def safe_filename(name):
    """
    Convert a lab name into a safe filename.
    Example: 'Ping Test Lab' -> 'Ping_Test_Lab.md'
    """
    return name.strip().replace(" ", "_").replace("/", "_").replace("\\", "_")


def update_readme(lab_name, filepath):
    """
    Add the new lab note to README.md under a Lab Index section.
    Uses a path relative to README location for portability.
    This updates locally only. It does NOT commit or push.
    """
    # Build path relative to README so links work on GitHub
    try:
        relative_path = filepath.relative_to(README_FILE.parent)
    except ValueError:
        # Fallback to absolute posix if relative resolution fails
        relative_path = filepath

    entry = f"- [{lab_name}]({relative_path.as_posix()})\n"

    # Create README if it does not exist
    if not README_FILE.exists():
        README_FILE.write_text("# Scribe\n\n## Lab Index\n", encoding="utf-8")

    # Read current README content
    content = README_FILE.read_text(encoding="utf-8")

    # Add Lab Index header if missing
    if "## Lab Index" not in content:
        content += "\n\n## Lab Index\n"

    # Add entry only if it does not already exist
    if entry not in content:
        content += entry

    # Save README
    README_FILE.write_text(content, encoding="utf-8")


def collect_terminal_output():
    """
    Collect multi-line terminal output from the user.
    Two consecutive blank lines signal end of input.
    Single blank lines are preserved (useful for command spacing).
    Returns the collected output as a single string.
    """
    print("\nPaste command output.")
    print("Press Enter TWICE on a blank line when done.\n")

    lines = []
    blank_count = 0

    while True:
        line = input()

        if line == "":
            blank_count += 1
            # Two consecutive blank lines = done
            if blank_count >= 2:
                break
            # Single blank line preserved in output
            lines.append(line)
        else:
            # Reset blank counter when non-empty line received
            blank_count = 0
            lines.append(line)

    # Strip any trailing blank lines added before the double-Enter
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def suggest_commit_message(lab_name):
    """
    Create a suggested git commit message.
    Human still approves before commit/push.
    """
    return f"Add Scribe lab note: {lab_name}"


def print_git_instructions(commit_message):
    """
    Print git commands for the approval gate.
    Scribe never runs git automatically — human reviews first.
    """
    print("\n" + "=" * 40)
    print("APPROVAL GATE — Review before running")
    print("=" * 40)
    print("\nSuggested git commands (run manually):\n")
    print("  git status")
    print("  git add .")
    print(f'  git commit -m "{commit_message}"')
    print("  git push")
    print("\nReview your output file and README.md before committing.")
    print("=" * 40)


# -----------------------------
# Startup
# -----------------------------

print(f"=== Scribe {VERSION} ===")

# Make sure output folder exists
OUTPUT_DIR.mkdir(exist_ok=True)

# Ask user for metadata about the lab
lab_name = input("Lab name: ")
objective = input("Objective: ")

# Collect terminal output using double-Enter sentinel
raw_output = collect_terminal_output()

# Require at least some output before continuing
if not raw_output.strip():
    print("\n[ERROR] No terminal output captured. Exiting.")
    raise SystemExit(1)

# Create timestamp for the lab note
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")


# -----------------------------
# Build AI Prompt
# -----------------------------

# Triple-quoted f-string must be opened and closed cleanly
# Note: closing ``` for the raw output block is inside the string
prompt = f"""You are Scribe, a local homelab/SOC documentation assistant.

Convert the user's terminal or lab output into a clean markdown lab note.

Rules:
- Be concise.
- Do not invent commands that were not shown unless clearly labeled as suggested next tests.
- Prefer practical troubleshooting over theory.
- Output ONLY markdown.
- Use practical language suitable for a beginner-to-junior infrastructure/security technician.

Use this exact structure:

## Observation
Explain what happened technically.

## Lesson Learned
Explain what this teaches about systems, networking, security, or troubleshooting.

## Suggested Next Commands
List useful next commands or tests. Clearly label them as suggested.

## Tags
Create 3 to 6 markdown hashtags like #networking #windows #dns #linux #security #troubleshooting.

## Interview Bullet
Create one resume/interview bullet based on this lab.

Lab name:
{lab_name}

Objective:
{objective}

Raw terminal output:
```text
{raw_output}
```
"""


# -----------------------------
# Send Prompt to Ollama
# -----------------------------

print(f"\nSending to Ollama ({MODEL})... ", end="", flush=True)

try:
    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    print("done.")

except Exception as e:
    # Surface a readable error if Ollama is not running or model is missing
    print(f"\n[ERROR] Ollama call failed: {e}")
    print(f"Is Ollama running? Try: ollama run {MODEL}")
    raise SystemExit(1)

# Extract only model response text
ai_analysis = response["message"]["content"]


# -----------------------------
# Build Markdown Report
# -----------------------------

markdown = (
    f"# {lab_name}\n\n"
    f"**Date:** {timestamp}\n\n"
    f"**Model:** {MODEL}\n\n"

    f"## Objective\n"
    f"{objective}\n\n"

    f"## Raw Output\n"
    f"```text\n{raw_output}\n```\n\n"

    f"## AI Analysis\n"
    f"{ai_analysis}\n"
)


# -----------------------------
# Save Markdown Report
# -----------------------------

# Create safe filename
filename = safe_filename(lab_name)

# Build full output path anchored to BASE_DIR
output_path = OUTPUT_DIR / f"{filename}.md"

# Save markdown file
output_path.write_text(markdown, encoding="utf-8")


# -----------------------------
# Update README Index
# -----------------------------

update_readme(lab_name, output_path)


# -----------------------------
# Approval Gate / Git Suggestion
# -----------------------------

commit_message = suggest_commit_message(lab_name)

# Confirm save
print(f"\nSaved: {output_path}")
print("Updated: README.md")

# Print git instructions — human runs these manually after review
print_git_instructions(commit_message)