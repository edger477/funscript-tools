from funscript.funscript import Funscript
import argparse

def mirror_up_funscript(funscript: Funscript, threshold: float) -> Funscript:
    # Create new arrays for modified points
    new_x = []
    new_y = []

    # Process each point
    for x, y in zip(funscript.x, funscript.y):
        new_x.append(x)  # Keep x values unchanged
        # Apply mirroring formula
        if y < threshold:
            y_new = 2 * threshold - y
        else:
            y_new = y
        new_y.append(y_new)

    # Create and return new funscript with modified points
    return Funscript(new_x, new_y)

def main(funscript_file: str, threshold: float, output_file: str):
    # Load the funscript file
    funscript = Funscript.from_file(funscript_file)

    # Process the funscript
    mirrored_funscript = mirror_up_funscript(funscript, threshold)

    # Save the modified funscript
    mirrored_funscript.save_to_path(output_file)
    print(f"Mirrored Funscript saved to {output_file}")

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Mirror points in a Funscript file based on a threshold.")
    parser.add_argument('filename', type=str, help="The path to the input Funscript file.")
    parser.add_argument('threshold', type=float, help="The threshold value for mirroring (0-0.5).")
    parser.add_argument('output_file', type=str, help="The path to save the mirrored Funscript file.")

    # Parse the arguments
    args = parser.parse_args()

    # Validate threshold
    if not (0 <= args.threshold <= 0.5):
        print("Error: Threshold must be between 0 and 0.5")
        exit(1)

    # Call the main function with the provided arguments
    main(args.filename, args.threshold, args.output_file)
