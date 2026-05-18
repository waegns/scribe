# Import timestamp tools
from datetime import datetime

# Import tools for file paths
from pathlib import Path

# Import regex for sanitization patterns
import re

# Import Python client for local Ollama models
import ollama


# -----------------------------
# Scribe Configuration
# -----------------------------

# Version label
VERSION = "v0.8"

# Local Ollama model to use
MODEL = "qwen2.5:14b"

# Anchor all paths to the directory this script lives in
# Prevents breakage when running from a different working directory
BASE_DIR = Path(__file__).parent.resolve()

# Obsidian vault root — portable across machines, no hardcoded username
# Change "Lab Work" if your vault folder is named differently
VAULT_ROOT = Path.home() / "Documents" / "Lab Work"

# Lab notes subfolder inside the vault (private, full detail)
VAULT_LAB_NOTES = VAULT_ROOT / "02 - Lab Notes"

# Obsidian index file — wiki-links, lives inside the vault
# Never committed to GitHub
OBSIDIAN_INDEX_FILE = VAULT_ROOT / "02 - Lab Notes" / "_Lab_Index.md"

# GitHub README — standard markdown links, lives in Scribe repo root
# Safe to commit and push
README_FILE = BASE_DIR / "README.md"

# Public sanitized output folder inside the Scribe repo
# These files are safe to commit and push to GitHub
PUBLIC_OUTPUT_DIR = BASE_DIR / "github-ready"

# DRY_RUN mode — set True to preview output without writing any files
# Use this when testing prompts or verifying Ollama responses
# Set False for normal operation
DRY_RUN = False

# SANITIZE_FOR_PUBLIC — set True to generate a scrubbed public version
# Writes sanitized note to github-ready/ folder alongside the vault note
# Raw output block is stripped; IPs, hostnames, tokens are redacted
SANITIZE_FOR_PUBLIC = True


# -----------------------------
# Sanitization Rules
# -----------------------------

# Known lab hostnames — extend this list as lab grows
# TODO: Future improvement — auto-detect via socket.hostname() or env var
#       so this list doesn't need manual maintenance as lab expands
LAB_HOSTNAMES = [
    "FOB", "M02", "OVERWATCH", "pfSense", "PowerSpec",
]

# Regex patterns for automatic redaction
# Each tuple: (compiled pattern, replacement string, label for warning)
SANITIZE_PATTERNS = [
    # Private IPv4 ranges: 192.168.x.x, 10.x.x.x, 172.16-31.x.x
    (re.compile(r'\b192\.168\.\d{1,3}\.\d{1,3}\b'), "<internal-ip>", "private-ip"),
    (re.compile(r'\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), "<internal-ip>", "private-ip"),
    (re.compile(r'\b172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b'), "<internal-ip>", "private-ip"),

    # MAC addresses
    (re.compile(r'\b([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}\b'), "<mac-address>", "mac-address"),

    # Email addresses
    (re.compile(r'\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b'), "<email>", "email"),

    # WireGuard interface names
    (re.compile(r'\bwg\d+\b', re.IGNORECASE), "<vpn-interface>", "vpn-interface"),

    # Long tokens: 32+ char alphanumeric strings
    # WARNING: known false positive risk on hashes, UUIDs, cert fingerprints,
    # and any legitimate long output string. Review approval gate output carefully.
    # If false positives become a problem, raise the threshold or add an allowlist.
    (re.compile(r'\b[A-Za-z0-9+/=_\-]{32,}\b'), "<redacted-token>", "token"),
]


def sanitize_text(text):
    """
    Scrub sensitive infrastructure details from text.
    Replaces IPs, hostnames, MAC addresses, emails, and tokens.
    Prints a warning report of what was redacted so the approval gate
    reviewer knows what fired — especially important for token false positives.
    Returns sanitized string safe for public publishing.
    """
    sanitized = text
    redaction_log = []

    # Replace known lab hostnames with generic placeholder
    for hostname in LAB_HOSTNAMES:
        pattern = re.compile(r'\b' + re.escape(hostname) + r'\b', re.IGNORECASE)
        matches = pattern.findall(sanitized)
        if matches:
            redaction_log.append(f"  hostname     : {len(matches)}x '{hostname}' → <lab-host>")
            sanitized = pattern.sub("<lab-host>", sanitized)

    # Apply all regex sanitization patterns
    for pattern, replacement, label in SANITIZE_PATTERNS:
        matches = pattern.findall(sanitized)
        if matches:
            # Flatten match tuples (from groups) to strings for display
            flat = [m if isinstance(m, str) else m[0] for m in matches]
            # Token warning gets extra attention — known false positive risk
            if label == "token":
                redaction_log.append(
                    f"  {label:<12} : {len(flat)}x match(es) — REVIEW: may include hashes, UUIDs, cert fingerprints"
                )
            else:
                redaction_log.append(f"  {label:<12} : {len(flat)}x match(es)")
            sanitized = pattern.sub(replacement, sanitized)

    # Print redaction report for approval gate review
    if redaction_log:
        print("\n[SANITIZER] Redactions applied to public note:")
        for entry in redaction_log:
            print(entry)
        print("  Review public note before committing.\n")
    else:
        print("\n[SANITIZER] No redactions applied. Verify manually if unexpected.\n")

    return sanitized


# -----------------------------
# Helper Functions
# -----------------------------

def safe_filename(name):
    """
    Convert a lab name into a safe filename.
    Example: 'Ping Test Lab' -> 'Ping_Test_Lab'
    """
    return name.strip().replace(" ", "_").replace("/", "_").replace("\\", "_")


def update_obsidian_index(lab_name, filename_stem):
    """
    Add the new lab note to the Obsidian index using wiki-link format.
    Lives inside the vault — never committed to GitHub.
    GitHub does not render [[wiki-links]].
    """
    # Obsidian wiki-link with display name
    entry = f"- [[{filename_stem}|{lab_name}]]\n"

    # Create index file if it does not exist
    if not OBSIDIAN_INDEX_FILE.exists():
        OBSIDIAN_INDEX_FILE.write_text(
            "# Lab Index\n\n"
            "> Auto-updated by Scribe. Do not edit manually.\n\n",
            encoding="utf-8"
        )

    # Read current index content
    content = OBSIDIAN_INDEX_FILE.read_text(encoding="utf-8")

    # Add entry only if it does not already exist
    if entry not in content:
        content += entry

    # Save index
    OBSIDIAN_INDEX_FILE.write_text(content, encoding="utf-8")


def update_github_readme(lab_name, public_filename):
    """
    Add the new public lab note to README.md using standard markdown links.
    Lives in the Scribe repo root — safe to commit and push to GitHub.
    Uses relative path so links resolve correctly on GitHub.
    """
    # Standard markdown link — GitHub renders these correctly
    relative_link = f"github-ready/{public_filename}"
    entry = f"- [{lab_name}]({relative_link})\n"

    # Create README if it does not exist
    if not README_FILE.exists():
        README_FILE.write_text(
            "# Scribe\n\n"
            "Local AI-powered lab documentation pipeline.\n\n"
            "## Lab Index\n\n"
            "> Sanitized public lab notes. "
            "Raw notes with full infrastructure detail are stored privately in Obsidian.\n\n",
            encoding="utf-8"
        )

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


def print_git_instructions(commit_message, public_filename):
    """
    Print git commands for the approval gate.
    Scribe never runs git automatically — human reviews first.
    Shows both file locations so reviewer knows what to check.
    """
    print("\n" + "=" * 40)
    print("APPROVAL GATE — Review before running")
    print("=" * 40)
    print("\nFiles to review:")
    print(f"  Private (Obsidian, never commit) : {VAULT_LAB_NOTES}")
    print(f"  Public  (GitHub safe)            : {PUBLIC_OUTPUT_DIR / public_filename}")
    print(f"  README  (GitHub safe)            : {README_FILE}")
    print(f"  Obsidian index (never commit)    : {OBSIDIAN_INDEX_FILE}")
    print("\nSuggested git commands (run manually):\n")
    print("  git status")
    print("  git add .")
    print(f'  git commit -m "{commit_message}"')
    print("  git push")
    print("\nDo NOT commit vault notes or Obsidian index to GitHub.")
    print("=" * 40)


def build_frontmatter(timestamp_date, tags, is_public=False):
    """
    Build YAML frontmatter block for Obsidian.
    Enables tag search, dataview queries, and graph filtering.
    Public version adds visibility: public flag for clarity.
    """
    tag_lines = "\n".join(f"  - {tag.strip('#')}" for tag in tags)
    visibility = "public" if is_public else "private"

    return (
        f"---\n"
        f"date: {timestamp_date}\n"
        f"type: lab\n"
        f"visibility: {visibility}\n"
        f"tags:\n"
        f"{tag_lines}\n"
        f"  - scribe\n"
        f"source: scribe\n"
        f"model: {MODEL}\n"
        f"---\n\n"
    )


def extract_tags(ai_analysis):
    """
    Pull hashtags out of the AI analysis Tags section.
    Returns a list of tag strings like ['#networking', '#windows'].
    Only captures words that start with # and have no space after —
    this excludes markdown headers like ## Observation which split into
    ['##', 'Observation'] and would otherwise produce empty tag entries.
    Falls back to a default set if none found.
    """
    tags = []

    for line in ai_analysis.splitlines():
        words = line.strip().split()
        for word in words:
            # Must start with # and next char must be a letter
            # Excludes ## headers, lone #, and punctuation
            if word.startswith("#") and len(word) > 1 and word[1].isalpha():
                tags.append(word)

    # Fall back to generic tags if AI didn't produce any
    if not tags:
        tags = ["#lab", "#scribe"]

    return tags


def build_private_note(lab_name, timestamp_display, objective, raw_output, ai_analysis, frontmatter):
    """
    Build the full private markdown note for Obsidian.
    Contains raw output, real IPs, hostnames — never committed to GitHub.
    """
    return (
        frontmatter +
        f"# {lab_name}\n\n"
        f"**Date:** {timestamp_display}\n\n"
        f"## Objective\n"
        f"{objective}\n\n"
        f"## Raw Output\n"
        f"```text\n{raw_output}\n```\n\n"
        f"## AI Analysis\n"
        f"{ai_analysis}\n"
    )


def build_public_note(lab_name, timestamp_display, objective, ai_analysis, frontmatter):
    """
    Build the sanitized public markdown note for GitHub.
    Raw output block excluded entirely — concepts and analysis only.
    All IPs, hostnames, and tokens are redacted.
    """
    # Sanitize objective and AI analysis — raw output never included
    clean_objective = sanitize_text(objective)
    clean_analysis = sanitize_text(ai_analysis)

    return (
        frontmatter +
        f"# {lab_name}\n\n"
        f"**Date:** {timestamp_display}\n\n"
        f"> *Sanitized for public publishing. "
        f"Raw output and infrastructure details are stored privately.*\n\n"
        f"## Objective\n"
        f"{clean_objective}\n\n"
        f"## AI Analysis\n"
        f"{clean_analysis}\n"
    )


# -----------------------------
# Startup
# -----------------------------

print(f"=== Scribe {VERSION} ===")

# Warn clearly if running in dry run mode
if DRY_RUN:
    print("[DRY RUN] No files will be written.\n")

# Warn if sanitization is off
if not SANITIZE_FOR_PUBLIC:
    print("[WARN] SANITIZE_FOR_PUBLIC is off. No public version will be generated.\n")

# Vault check — fail loudly if scaffold hasn't been run
if not DRY_RUN and not VAULT_LAB_NOTES.exists():
    print(f"\n[ERROR] Vault lab notes folder not found:")
    print(f"  {VAULT_LAB_NOTES}")
    print("Run ironforge_scaffold.py first to build the vault.")
    raise SystemExit(1)

# Create public output folder if needed
if not DRY_RUN and SANITIZE_FOR_PUBLIC:
    PUBLIC_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Ask user for metadata about the lab
lab_name = input("Lab name: ")
objective = input("Objective: ")

# Collect terminal output using double-Enter sentinel
raw_output = collect_terminal_output()

# Require at least some output before continuing
if not raw_output.strip():
    print("\n[ERROR] No terminal output captured. Exiting.")
    raise SystemExit(1)

# Timestamps
now = datetime.now()
timestamp_display = now.strftime("%Y-%m-%d %H:%M")
timestamp_date = now.strftime("%Y-%m-%d")
timestamp_file = now.strftime("%Y-%m-%d_%H%M")


# -----------------------------
# Build AI Prompt
# -----------------------------

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
    print(f"\n[ERROR] Ollama call failed: {e}")
    print(f"Is Ollama running? Try: ollama run {MODEL}")
    raise SystemExit(1)

# Extract model response text
ai_analysis = response["message"]["content"]

# Pull tags for frontmatter
tags = extract_tags(ai_analysis)


# -----------------------------
# Build Both Notes
# -----------------------------

# Shared filename stem — same base for both versions
filename_stem = f"{timestamp_file}_{safe_filename(lab_name)}"
public_filename = f"Public_{filename_stem}.md"

# Private note — full detail, vault only
private_frontmatter = build_frontmatter(timestamp_date, tags, is_public=False)
private_markdown = build_private_note(
    lab_name, timestamp_display, objective,
    raw_output, ai_analysis, private_frontmatter
)

# Public note — sanitized, GitHub safe
public_frontmatter = build_frontmatter(timestamp_date, tags, is_public=True)
public_markdown = build_public_note(
    lab_name, timestamp_display, objective,
    ai_analysis, public_frontmatter
)


# -----------------------------
# Save or Dry Run
# -----------------------------

if DRY_RUN:
    print("\n" + "=" * 40)
    print("DRY RUN — PRIVATE NOTE (Obsidian)")
    print("=" * 40)
    print(private_markdown)

    print("\n" + "=" * 40)
    print("DRY RUN — PUBLIC NOTE (GitHub)")
    print("=" * 40)
    print(public_markdown)

    print("\nDry run complete. Set DRY_RUN = False to write files.")

else:
    # Save private note to Obsidian vault
    private_path = VAULT_LAB_NOTES / f"{filename_stem}.md"
    private_path.write_text(private_markdown, encoding="utf-8")
    print(f"\nPrivate note saved : {private_path}")

    # Update Obsidian index with wiki-link (vault only, never GitHub)
    update_obsidian_index(lab_name, filename_stem)
    print(f"Obsidian index     : updated")

    if SANITIZE_FOR_PUBLIC:
        # Save public note to github-ready folder
        public_path = PUBLIC_OUTPUT_DIR / public_filename
        public_path.write_text(public_markdown, encoding="utf-8")
        print(f"Public note saved  : {public_path}")

        # Update GitHub README with standard markdown link
        update_github_readme(lab_name, public_filename)
        print(f"README updated     : {README_FILE}")

    # Print approval gate with both file locations
    commit_message = suggest_commit_message(lab_name)
    print_git_instructions(commit_message, public_filename)
