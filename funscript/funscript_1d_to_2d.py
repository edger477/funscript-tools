# credit @diglet48 https://github.com/diglet48/restim/blob/master/funscript/funscript_conversion.py
import numpy as np
import json
import argparse


def parse_funscript(path):
    x = []
    y = []
    with open(path) as f:
        js = json.load(f)
        for action in js['actions']:
            at = float(action['at']) / 1000
            pos = float(action['pos']) * 0.01
            x.append(at)
            y.append(pos)
    return x, y


def write_funscript(path, funscript):
    x, y = funscript
    actions = [{"at": int(at*1000), "pos": int(pos * 100)} for at, pos in zip(x, y)]
    js = {"actions": actions}
    with open(path, 'w') as f:
        json.dump(js, f)


def convert_funscript_radial(funscript, min_distance_from_center=0.1, speed_at_edge_hz=2.0):
    at, pos = funscript

    t_out = []
    x_out = []
    y_out = []

    # Convert speed_at_edge_hz to time needed to go from 0 to 1
    # If speed_at_edge_hz = 2Hz, then full range (0 to 1) takes 0.5 seconds
    max_speed_threshold = abs(1.0) / (1.0 / speed_at_edge_hz)  # Speed for full range in 1/Hz seconds

    for i in range(len(pos)-1):
        start_t, end_t = at[i:i+2]
        start_p, end_p = pos[i:i+2]

        points_per_second = 25
        n = int(np.clip(float((end_t - start_t) * points_per_second), 1, None))

        # Calculate speed for this segment (position change per second)
        segment_duration = end_t - start_t
        position_change = abs(end_p - start_p)
        current_speed = position_change / segment_duration if segment_duration > 0 else 0

        # Map speed to radius (min_distance_from_center to 1.0)
        speed_ratio = min(current_speed / max_speed_threshold, 1.0)  # Clamp to 1.0
        radius_scale = min_distance_from_center + (1.0 - min_distance_from_center) * speed_ratio

        t = np.linspace(0.0, end_t - start_t, n, endpoint=False)
        theta = np.linspace(0, np.pi, n, endpoint=False)
        center = (end_p + start_p) / 2
        r = (start_p - end_p) / 2

        # Apply speed-based radius scaling
        r = r * radius_scale

        x = center + r * np.cos(theta)
        y = r * np.sin(theta) + 0.5
        t_out += list(t + start_t)
        x_out += list(x)
        y_out += list(y)

    return t_out, x_out, y_out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='funscript conversion',
        description='convert 1d funscript into 2d')

    parser.add_argument('filename')

    args = parser.parse_args()
    in_filename = args.filename
    alpha_filename = in_filename.replace('.funscript', '.alpha.funscript')
    beta_filename = in_filename.replace('.funscript', '.beta.funscript')

    print('in   : {}'.format(in_filename))
    print('out a: {}'.format(alpha_filename))
    print('out b: {}'.format(beta_filename))

    funscript = parse_funscript(in_filename)
    print('convert...')
    a, b, c = convert_funscript_radial(funscript)
    print('write...')
    write_funscript(alpha_filename, (a, b))
    write_funscript(beta_filename, (a, c))
    print('done')
