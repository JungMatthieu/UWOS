import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--output_file')
parser.add_argument('--duration', type=int)
parser.add_argument('--width', type=int)
parser.add_argument('--height', type=int)
parser.add_argument('--framerate', type=int)
parser.add_argument('--codec')
parser.add_argument('--bitrate', type=int)
parser.add_argument('--nopreview', type=lambda x: x.lower() == 'true')
parser.add_argument('--disable_display_flag', type=lambda x: x.lower() == 'true')

args = parser.parse_args()

# Tu peux ensuite appeler record_video avec ces paramètres :
from sub_rec import record_video

record_video(
    args.output_file,
    args.duration,
    args.width,
    args.height,
    args.framerate,
    args.codec,
    args.bitrate,
    args.nopreview,
    args.disable_display_flag
)
