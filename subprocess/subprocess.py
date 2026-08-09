import subprocess

import argparse
parser = argparse.ArgumentParser(description="subprocess")
parser.add_argument(
    "command",
    type=str,
    help="Command",
)
parser.add_argument(
    "-hide","--hide",
    action="store_true",
    help="Hide cmd window",
)

args = parser.parse_args()

print("start subprocess", args.command)
if args.hide:
    print("hide cmd window")
    subprocess.Popen(args.command, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
else:
    print("show cmd window")
    subprocess.Popen(args.command, shell=False)
print("subprocess done")
