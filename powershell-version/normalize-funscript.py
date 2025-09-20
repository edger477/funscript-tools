import json
import sys
import os

def normalize_funscript(filename):
    # Load the funscript
    with open(filename, 'r') as f:
        data = json.load(f)

    actions = data.get('actions', [])
    if not actions:
        print("No actions found in funscript.")
        return

    max_pos = max(a['pos'] for a in actions)
    shift = 100 - max_pos

    print(f"Max position: {max_pos} → Shifting all by +{shift}")

    # Shift all positions up, cap at 100
    for action in actions:
        action['pos'] = min(100, action['pos'] + shift)

    # Save with "_normalized" suffix
    base, ext = os.path.splitext(filename)
    output_filename = f"{base}_normalized{ext}"
    with open(output_filename, 'w') as f:
        json.dump(data, f, indent=4)

    print(f"Normalized funscript saved as {output_filename}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python normalize_funscript.py <filename>")
        sys.exit(1)

    normalize_funscript(sys.argv[1])
