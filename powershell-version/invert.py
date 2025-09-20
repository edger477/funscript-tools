import json
import sys
import os

def invert_funscript(filename):
    # Load the Funscript
    with open(filename, 'r') as f:
        data = json.load(f)

    # Invert all positions
    for action in data['actions']:
        action['pos'] = 100 - action['pos']

    # Create output filename
    base, ext = os.path.splitext(filename)
    output_filename = f"{base}_inverted{ext}"

    # Save the inverted Funscript
    with open(output_filename, 'w') as f:
        json.dump(data, f, indent=4)

    print(f"Inverted funscript saved as {output_filename}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python invert_funscript.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]
    invert_funscript(filename)
