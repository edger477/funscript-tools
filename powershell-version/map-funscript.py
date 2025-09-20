from funscript.funscript import Funscript
import argparse

def map_funscript(funscript: Funscript, new_min: float, new_max: float) -> Funscript:
    # Find current min and max
    current_min = min(funscript.y)
    current_max = max(funscript.y)

    # Create new arrays for modified points
    new_x = []
    new_y = []

    # Process each point
    for x, y in zip(funscript.x, funscript.y):
        new_x.append(x)  # Keep x values unchanged
        # Apply linear mapping formula
        y_new = (y - current_min) / (current_max - current_min) * (new_max - new_min) + new_min
        new_y.append(y_new)

    # Create and return new funscript with modified points
    return Funscript(new_x, new_y)

def main(funscript_file: str, new_min: float, new_max: float, output_file: str):
    # Load the funscript file
    funscript = Funscript.from_file(funscript_file)

    # Process the funscript
    mapped_funscript = map_funscript(funscript, new_min, new_max)

    # Save the modified funscript
    mapped_funscript.save_to_path(output_file)
    print(f"Mapped Funscript saved to {output_file}")

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Linearly map points in a Funscript file to a new range.")
    parser.add_argument('funscript_file', type=str, help="The path to the input Funscript file.")
    parser.add_argument('new_min', type=float, help="The new minimum value for the funscript points.")
    parser.add_argument('new_max', type=float, help="The new maximum value for the funscript points.")
    parser.add_argument('output_file', type=str, help="The path to save the modified Funscript file.")

    # Parse the arguments
    args = parser.parse_args()

    # Call the main function with the provided arguments
    main(args.funscript_file, args.new_min, args.new_max, args.output_file)
