import argparse
import os
import re
import subprocess
import sys

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

from dataclasses import dataclass
from datetime import datetime, timedelta
from pprint import pprint
from typing import Dict

# this was made with cloc version 2.02, but its format should be stable.
ENV_DEPS = ['git', 'cloc']

SECONDS_IN_DAY = 3600 * 24
MAX_COMMITS_EXAMINED = 30
LINE_STYLE = "-"
LINE_WIDTH = 2
POINT_STYLE = "."

# short alias for run shell command
sh = subprocess.getstatusoutput

def assert_sh(command):
    exit_code, output = sh(command)
    if exit_code != 0:
        raise Exception(f'Error when running shell command `{command}`:\n' + output)
    return output


def check_env_dep(command):
    exit_code, _ = sh(f"which {command}")
    if exit_code != 0:
        print(f"Error: {command} not installed")
        sys.exit(1)

def check_env_deps():
    """Check that necessary commands are installed and accessible from the shell"""
    for command in ENV_DEPS:
        check_env_dep(command)

@dataclass
class ClocLang:
    files: int
    blank: int
    comment: int
    code: int

@dataclass
class Cloc:
    total: ClocLang
    langs: Dict[str, ClocLang]
    timestamp: datetime

def parse_cloc_lang(line: str) -> tuple[str, ClocLang]:
    tokens = re.split(r'\s\s+', line)
    [lang, *counts] = tokens
    keys = ['files', 'blank', 'comment', 'code']
    counts_dict = {k: int(v) for k, v in zip(keys, counts)}
    return lang, ClocLang(**counts_dict)

def count_lines_in_commit(hash, idx=None, length=None) -> Cloc | None:
    if idx and length:
        width = len(str(length))
        print(f'\r{(idx+1):>{width}}/{length} Counting lines in commit hash {hash}', end="")
    else:
        print(f'Counting lines in commit hash {hash}')
    checkout(hash)
    timestamp = get_commit_time(hash)

    cloc_lines = assert_sh('cloc . --VCS=git --exclude-ext=json').split("\n")
    _, total = parse_cloc_lang(cloc_lines[-2])

    langs = {}
    for line in cloc_lines[4:-3]:
        lang, lang_counts = parse_cloc_lang(line) 
        langs[lang] = lang_counts

    return Cloc(langs=langs, total=total, timestamp=timestamp)

def checkout(obj):
    assert_sh(f'git checkout --force {obj}')

def get_current_commit_time() -> datetime:
    return datetime.fromisoformat(assert_sh('git --no-pager show -s --format=%cI HEAD'))

def get_commit_time(hash) -> datetime:
    return datetime.fromisoformat(assert_sh(f'git --no-pager show -s --format=%cI {hash}'))

def get_first_commit_after_time(hashes, timestamp):
    low = 0
    high = len(hashes) - 1
    while low <= high:
        mid = (high + low) // 2
        t = get_commit_time(hashes[mid])
        if t == timestamp:
            return hashes[mid]
        elif t > timestamp:
            if mid == 0:
                return hashes[mid]
            else:
                t_prev = get_commit_time(hashes[mid-1])
                if t_prev < timestamp:
                    return hashes[mid]
        if t < timestamp:
            low = mid + 1
        else:
            high = mid - 1

    return None

def count_lines_in_branch(branch) -> list[Cloc]:
    original_checked_out_branch = assert_sh('git rev-parse --abbrev-ref HEAD')
    checkout(branch)
    num_commits = int(assert_sh('git rev-list --count HEAD'))

    # these commits will be in ascending time order
    commit_hashes = assert_sh('git rev-list --no-abbrev-commit --reverse HEAD').split("\n")

    # figure out how many we actually want
    first_commit_time = get_commit_time(commit_hashes[0])
    last_commit_time = get_commit_time(commit_hashes[-1])

    td = last_commit_time - first_commit_time
    seconds = td.days * SECONDS_IN_DAY + td.seconds


    selected_commit_hashes = []
    if num_commits > MAX_COMMITS_EXAMINED:
        format_width = len(str(MAX_COMMITS_EXAMINED))
        min_times = [first_commit_time + timedelta(seconds=n) for n in np.linspace(0, seconds, num=MAX_COMMITS_EXAMINED, endpoint=True)]
        for timestamp in min_times:
            hash = get_first_commit_after_time(commit_hashes, timestamp)
            if hash:
                if len(selected_commit_hashes) == 0 or hash != selected_commit_hashes[-1]:
                    selected_commit_hashes.append(hash)
                    print(f"\rFound {len(selected_commit_hashes):>{format_width}}/{MAX_COMMITS_EXAMINED} commits", end="")
            else:
                break

        print()
    else:
        selected_commit_hashes = commit_hashes

    print(f"Counting lines in {len(selected_commit_hashes)} commits in {branch}")
    try:
        clocs = []
        for i, hash in enumerate(selected_commit_hashes):
            cloc = count_lines_in_commit(hash, i, len(selected_commit_hashes))
            if cloc:
                clocs.append(cloc)
        print()

        assert_sh(f'git checkout {original_checked_out_branch}')
        return clocs
    except Exception as e:
        print(e)
        # when done, make sure we clean up by checking out the current branch
        assert_sh(f'git checkout {original_checked_out_branch}')
        raise e

def main():
    check_env_deps()

    parser = argparse.ArgumentParser()
    parser.add_argument('path', help='path to git repo')
    parser.add_argument('-b', '--branch', help='branch in git repo')
    parser.add_argument('-a', '--all', help='whether or not to show totals for all languages', action=argparse.BooleanOptionalAction)
    args = vars(parser.parse_args())
    path, branch, plot_all = [args[k] for k in ['path', 'branch', 'all']]
    os.chdir(path)

    clocs = count_lines_in_branch(branch)
    if len(clocs) == 0:
        print(f'No commits found in branch {branch}')

    # Create a figure and axis
    _, ax = plt.subplots(layout='constrained')

    if plot_all:
        top_langs = [(clocs[-1].langs[lang].code, lang) for lang in clocs[-1].langs]
        top_langs.sort(reverse=True)
        top_langs = top_langs[:10]

        langs = set([lang for _, lang in top_langs])

        data = {lang: [] for lang in langs}
        total = []
        times = []
        for cloc in clocs:
            for lang in langs:
                if lang in cloc.langs:
                    data[lang].append(cloc.langs[lang].code)
                else:
                    data[lang].append(0)
            total.append(cloc.total.code)
            times.append(cloc.timestamp)

        # Plot each language
        for lang in data:
            plt.plot(times, data[lang], POINT_STYLE, label=f'{lang}', linestyle=LINE_STYLE, linewidth=LINE_WIDTH)
        plt.plot(times, total, POINT_STYLE, label=f'Total', linestyle=LINE_STYLE, linewidth=LINE_WIDTH)
    else:
        total = []
        times = []
        for cloc in clocs:
            total.append(cloc.total.code)
            times.append(cloc.timestamp)
        plt.plot(times, total, POINT_STYLE, label=f'Total', linestyle=LINE_STYLE, linewidth=LINE_WIDTH)

    # Customize the plot
    plt.title(f'Lines of code in {branch}')
    ax.set_yscale('linear')
    for label in ax.get_xticklabels():
        label.set_rotation(40)
        label.set_horizontalalignment('right')
    plt.ylabel('Meaningful lines of code')
    plt.legend()

    # Show the plot
    plt.show()

if __name__ == "__main__":
    main()
