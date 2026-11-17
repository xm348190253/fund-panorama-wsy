#!/usr/bin/env python3
"""Run a pipeline command within the one-date presentation update deadline."""
import argparse
import datetime as dt
import os
import signal
import subprocess
from cloud_refresh_gate import TZ, presentation_deadline


def remaining_seconds(now, reserve_seconds=0):
    deadline = presentation_deadline(now)
    if deadline is None:
        return None
    return max(0, (deadline - now.astimezone(TZ)).total_seconds() - reserve_seconds)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reserve-seconds', type=int, default=0)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or args.reserve_seconds < 0:
        parser.error('A command and a nonnegative time reserve are required.')
    budget = remaining_seconds(dt.datetime.now(TZ), args.reserve_seconds)
    if budget is not None and budget <= 0:
        print('Presentation update deadline reached; retain the last verified publication.', flush=True)
        return 124
    if budget is not None:
        print('2026-11-18 update budget: ' + str(int(budget)) + ' seconds.', flush=True)
    process = subprocess.Popen(command, start_new_session=True)
    try:
        return process.wait(timeout=budget)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        print('Presentation update command exceeded its time budget.', flush=True)
        return 124


if __name__ == '__main__':
    raise SystemExit(main())
