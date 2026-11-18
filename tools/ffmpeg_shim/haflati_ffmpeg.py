"""Puts an `ffmpeg` command on PATH that runs the static build bundled by imageio-ffmpeg,
so the runner never needs a slow apt install."""
import os, sys


def main():
    import imageio_ffmpeg
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    os.execv(exe, [exe] + sys.argv[1:])
