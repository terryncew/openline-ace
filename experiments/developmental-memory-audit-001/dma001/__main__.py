from __future__ import annotations
import argparse, json
from .grader import grade_file

def main():
    p = argparse.ArgumentParser(prog="dma001")
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("grade")
    g.add_argument("--results", required=True)
    args = p.parse_args()
    if args.cmd == "grade":
        print(json.dumps(grade_file(args.results), indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
