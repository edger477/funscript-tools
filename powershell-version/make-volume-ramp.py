import json
import argparse

def load_funscript(file_path):
    """Load a funscript file and return the full data."""
    with open(file_path, 'r') as f:
        return json.load(f)

def save_funscript(data, output_path):
    """Save the funscript data to a new file."""
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=4)

def trim_and_adjust_funscript(funscript_data):
    """Keep only first 2 and last 2 points and adjust positions."""
    actions = funscript_data['actions']
    
    if len(actions) < 4:
        raise ValueError("Funscript must have at least 4 actions to perform this operation.")

    # Keep first 2 and last 2
    trimmed_actions = [actions[0], actions[1], actions[-2], actions[-1]]

    # Set positions
    trimmed_actions[0]['pos'] = 0     # first point
    trimmed_actions[1]['pos'] = 80    # second point (0.5)
    trimmed_actions[2]['pos'] = 100   # third point (1.0)
    trimmed_actions[3]['pos'] = 0     # fourth point

    # Replace actions in data
    funscript_data['actions'] = trimmed_actions
    return funscript_data

def main(input_file, output_file):
    funscript_data = load_funscript(input_file)
    modified_data = trim_and_adjust_funscript(funscript_data)
    save_funscript(modified_data, output_file)
    print(f"Modified Funscript saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trim a Funscript to 4 points and adjust their values.")
    parser.add_argument('input_file', type=str, help="Path to the input Funscript file.")
    parser.add_argument('output_file', type=str, help="Path to the output Funscript file.")
    args = parser.parse_args()

    main(args.input_file, args.output_file)
