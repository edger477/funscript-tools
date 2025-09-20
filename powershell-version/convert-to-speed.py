from funscript.funscript import Funscript
import numpy as np
import argparse




def calculate_speed(funscript):
    """Calculate the absolute speed of change between consecutive points."""
    x = []
    y = []
    max_speed = 0

    # Iterate over consecutive points
    for i in range(1, len(funscript.x)):
        time_diff = (funscript.x[i] - funscript.x[i - 1]) * 1000  # Time difference in milliseconds
        pos_diff = abs(funscript.y[i] - funscript.y[i - 1])  # Absolute position change

        # Avoid division by zero if time_diff is zero
        if time_diff != 0:
            speed = pos_diff / time_diff  # Speed (change per millisecond)
        else:
            speed = 0

        if speed > max_speed:
            max_speed = speed




        # Append the new action with speed as the 'pos' value and original timestamp
        x.append((funscript.x[i-1]))
        y.append(speed)

    factor = 1 / max_speed
    for i in range(1, len(y)):
        y[i] = y[i] * factor
    return Funscript(x, y)

def add_interpolated_points(funscript_data):
    """
    Given x = timestamps (ms) and y = positions (0-100),
    interpolate so that there's one value every 1000 ms.
    """
    if len(funscript_data.x) < 2:
        raise ValueError("Need at least two points to interpolate.")

    x = np.array(funscript_data.x)
    y = np.array(funscript_data.y)

    start = int(x[0])
    end = int(x[-1])

    # Generate timestamps every 1000ms
    target_x = np.arange(start, end + 1, 0.1)

    # Interpolate positions at those timestamps
    interp_y = np.interp(target_x, x, y)

    # Convert to lists and round positions
    funscript_data.x = target_x.tolist()
    #funscript_data.y = [int(round(p)) for p in interp_y]
    funscript_data.y = interp_y.tolist()

    return funscript_data

def calculate_speed_windowed(funscript, seconds):
    """Calculate the rolling average speed of change over the last n seconds."""
    x = []
    y = []
    max_speed = 0
    time_window = seconds
    shift = time_window * 5

    # Iterate over each point
    x.append(funscript.x[0])
    y.append(0) 

    for i in range(1 + shift, len(funscript.x)):
        current_time = funscript.x[i]
        pos_current = funscript.y[i]

        # Initialize variables for rolling sum
        total_speed = 0
        count = 0

        # Look back at all points within the last n seconds
        for j in range(i, -1, -1):
            if current_time - funscript.x[j] > time_window:
                break  # Stop if we're outside the n-second window

            time_diff = funscript.x[j] - funscript.x[j-1]  # Time difference in milliseconds
            pos_diff = abs(funscript.y[j] - funscript.y[j-1])  # Absolute position change

            # Avoid division by zero if time_diff is zero
            if time_diff != 0:
                speed = pos_diff / time_diff  # Speed (change per millisecond)
                total_speed += speed
                count += 1

        # Calculate the average speed over the rolling window
        avg_speed = (total_speed / count) if count > 0 else 0

        if avg_speed > max_speed:
            max_speed = avg_speed

        # Append the new action with average speed as the 'pos' value

        # Append the new action with speed as the 'pos' value and original timestamp
        # distance_to_next_point = funscript.x[i + 1] - funscript.x[i] if i < len(funscript.x) - 1 else 0
        # distance_to_previous_point = funscript.x[i] - funscript.x[i-1] if i > 0 else distance_to_next_point

        # if distance_to_next_point > distance_to_previous_point * 5:
        #     x.append(funscript.x[i-1] + distance_to_previous_point)
        #     y.append(avg_speed)
        
        
        x.append((funscript.x[i-shift]))
        y.append(avg_speed)

    x.append(funscript.x[len(funscript.x)-1])
    y.append(0)
        

    factor = 1 / max_speed
    for i in range(len(y)):
        y[i] = y[i] * factor

    return Funscript(x, y)




def main(funscript_file, output_file, seconds):
    # Load the funscript files
    funscript = Funscript.from_file(funscript_file)
    
    funscript = add_interpolated_points(funscript)

    # Combine the funscripts
    speed = calculate_speed_windowed(funscript, seconds)

    # Save the combined funscript
    speed.save_to_path(output_file)
    print(f"Speed Funscript saved to {output_file}")


if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Convert speed of input funscript to output.")
    parser.add_argument('funscript_input', type=str, help="The path to the input Funscript file.")
    parser.add_argument('funscript_output', type=str, help="The path to the output Funscript file.")
    
    parser.add_argument('seconds', type=int,
                        help="Size of window over which to measure speed (in seconds)", default=10)

    # Parse the arguments
    args = parser.parse_args()

    # Call the main function with the provided arguments
    # main(args.funscript_file1, args.funscript_file2, args.output_file)
    main(args.funscript_input, args.funscript_output, args.seconds)
