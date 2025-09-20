from funscript.funscript import Funscript
import numpy as np
import argparse

def multiply_funscripts(left: Funscript, right: Funscript) -> Funscript:
    x = np.union1d(left.x, right.x)
    y = np.interp(x, left.x, left.y) * np.interp(x, right.x, right.y)
    return Funscript(x, y)


def avg_funscripts(left: Funscript, right: Funscript, ratio, rest_level: float) -> Funscript:
    x = np.union1d(left.x, right.x)

    # Interpolate both signals
    y_left = np.interp(x, left.x, left.y)
    y_right = np.interp(x, right.x, right.y)

    # Calculate the averaged output
    y = (y_left * (ratio - 1) + y_right) / ratio

    # Apply rest_level when either input is 0
    y = np.where(
        (y_left == 0) | (y_right == 0),
        y * rest_level,
        y
    )

    return Funscript(x, y)



def main(funscript_file1, funscript_file2, output_file, ratio, rest_level):
    # Load the funscript files
    funscript1 = Funscript.from_file(funscript_file1)
    funscript2 = Funscript.from_file(funscript_file2)

    # Combine the funscripts
    combined_actions = avg_funscripts(funscript1, funscript2, ratio, rest_level)

    # Save the combined funscript
    combined_actions.save_to_path(output_file)
    print(f"Combined Funscript saved to {output_file}")

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Combine two Funscript files by multiplying their position values.")
    parser.add_argument('funscript_file1', type=str, help="The path to the first input Funscript file.")
    parser.add_argument('funscript_file2', type=str, help="The path to the second input Funscript file.")
    parser.add_argument('output_file', type=str, help="The path to save the combined Funscript file.")
    #parser.add_argument('filename', type=str, help="The file name. We combine filename.volume_ramp.funscript with filename.speed.funscript into filename.volume.funscript")
    parser.add_argument('ratio', type=int, help="The ratio between scripts, 2 for 50/50, 4 for 75/25 etc", default=2)
    parser.add_argument('--rest_level', type=float, help="Multiplier for output when either input is 0 (0.0 to 1.0)", default=0.5)

    # Parse the arguments
    args = parser.parse_args()

    # Call the main function with the provided arguments
    main(args.funscript_file1, args.funscript_file2, args.output_file, args.ratio, args.rest_level)
    #main(args.filename + ".volume_ramp.funscript", args.filename + ".speed.funscript", args.filename + ".volume.funscript", args.ratio)
