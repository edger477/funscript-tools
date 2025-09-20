from funscript.funscript import Funscript
import argparse

def limit_funscript(funscript: Funscript, new_min: float, new_max: float) -> Funscript:
    # Create new arrays for modified points
    new_x = []
    new_y = []

    # Process each point
    for x, y in zip(funscript.x, funscript.y):
        new_x.append(x)  # Keep x values unchanged
        # Apply limiting formula
        y_new = min(max(y, new_min), new_max)
        new_y.append(y_new)

    # Create and return new funscript with modified points
    return Funscript(new_x, new_y)

def main(funscript_file: str, new_min: float, new_max: float, output_file: str):
    # Load the funscript file
    funscript = Funscript.from_file(funscript_file)

    # Process the funscript
    limited_funscript = limit_funscript(funscript, new_min, new_max)

    # Save the modified funscript
    limited_funscript.save_to_path(output_file)
    print(f"Limited Funscript saved to {output_file}")

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Limit points in a Funscript file to a new range.")
    parser.add_argument('funscript_file', type=str, help="The path to the input Funscript file.")
    parser.add_argument('new_min', type=float, help="The new minimum value for the funscript points.")
    parser.add_argument('new_max', type=float, help="The new maximum value for the funscript points.")
    parser.add_argument('output_file', type=str, help="The path to save the modified Funscript file.")

    # Parse the arguments
    args = parser.parse_args()

    # Call the main function with the provided arguments
    main(args.funscript_file, args.new_min, args.new_max, args.output_file)
