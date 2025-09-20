from funscript.funscript import Funscript
import argparse

def shift_funscript(funscript: Funscript, threshold_percent: int, shift_percent: int) -> Funscript:
    # Convert percentages to decimals
    threshold = threshold_percent / 100
    shift_factor = shift_percent / 100
    
    # Create new arrays for modified points
    new_x = []
    new_y = []
    
    # Process each point
    for x, y in zip(funscript.x, funscript.y):
        new_x.append(x)  # Keep x values unchanged
        if y > threshold:
            # Apply shift formula: y = y + ((1-y) * shift_factor)
            # This ensures y values never exceed 1.0 and approach it asymptotically
            new_y.append(y + ((1 - y) * shift_factor))
        else:
            new_y.append(y)
    
    # Create and return new funscript with modified points
    return Funscript(new_x, new_y)

def main(funscript_file: str, threshold: int, shift_by: int):
    # Load the funscript file
    funscript = Funscript.from_file(funscript_file)
    
    # Process the funscript
    shifted_funscript = shift_funscript(funscript, threshold, shift_by)
    
    # Save the modified funscript
    output_file = f"{funscript_file.rsplit('.', 1)[0]}_shifted.funscript"
    shifted_funscript.save_to_path(output_file)
    print(f"Shifted Funscript saved to {output_file}")

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Shift points in a Funscript file based on threshold and shift percentage.")
    parser.add_argument('funscript_file', type=str, help="The path to the input Funscript file.")
    parser.add_argument('threshold', type=int, help="Threshold percentage (0-100). Points with x > threshold will be shifted.")
    parser.add_argument('shift_by', type=int, help="Shift percentage (0-100). Points will be shifted by x * shift_by/100.")
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Validate percentages
    if not (0 <= args.threshold <= 100 and 0 <= args.shift_by <= 100):
        print("Error: Both threshold and shift_by must be between 0 and 100")
        exit(1)
    
    # Call the main function with the provided arguments
    main(args.funscript_file, args.threshold, args.shift_by) 