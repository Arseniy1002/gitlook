#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess
from pathlib import Path

NO_COLOR = os.environ.get("NO_COLOR") is not None

def col(text, code):
    if NO_COLOR or not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"

def red(t): return col(t, "31")
def green(t): return col(t, "32")
def yellow(t): return col(t, "33")
def cyan(t): return col(t, "36")
def dim(t): return col(t, "2")
def bold(t): return col(t, "1")

def run_git(repo_path, *args):
    try:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip(), result.returncode
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "", 1

def get_repo_info(path):
    branch, rc = run_git(path, "rev-parse", "--abbrev-ref", "HEAD")
    if rc != 0:
        return None

    status_out, _ = run_git(path, "status", "--porcelain")
    dirty_count = len(status_out.splitlines()) if status_out else 0

    stash_out, _ = run_git(path, "stash", "list")
    stash_count = len(stash_out.splitlines()) if stash_out else 0

    unpushed = 0
    ahead_out, rc = run_git(path, "rev-list", "--count", f"@{{u}}..HEAD")
    if rc == 0 and ahead_out.isdigit():
        unpushed = int(ahead_out)

    unpulled = 0
    behind_out, rc = run_git(path, "rev-list", "--count", f"HEAD..@{{u}}")
    if rc == 0 and behind_out.isdigit():
        unpulled = int(behind_out)

    last_commit_msg, _ = run_git(path, "log", "-1", "--format=%s")
    last_commit_age, _ = run_git(path, "log", "-1", "--format=%cr")

    return {
        "name": path.name,
        "branch": branch,
        "dirty": dirty_count,
        "unpushed": unpushed,
        "unpulled": unpulled,
        "stashes": stash_count,
        "last_msg": last_commit_msg[:50] if last_commit_msg else "-",
        "last_age": last_commit_age or "-",
    }

def find_repos(root, depth=2):
    root = Path(root).resolve()
    repos = []
    
    if (root / ".git").exists():
        repos.append(root)
        return repos

    for current_depth in range(1, depth + 1):
        pattern = "/".join(["*"] * current_depth) + "/.git"
        for git_dir in root.glob(pattern):
            repo = git_dir.parent
            if repo not in repos:
                repos.append(repo)

    repos.sort(key=lambda p: p.name.lower())
    return repos

def fmt_status_cell(count, label, color_fn):
    if count == 0:
        return dim("0 " + label)
    return color_fn(f"{count} {label}")

def print_table(repos_data, show_clean):
    if not show_clean:
        repos_data = [r for r in repos_data if r["dirty"] or r["unpushed"] or r["unpulled"] or r["stashes"]]

    if not repos_data:
        print(dim("  nothing to show — everything looks clean"))
        return

    name_w = max(len(r["name"]) for r in repos_data)
    name_w = max(name_w, 4)
    branch_w = max(len(r["branch"]) for r in repos_data)
    branch_w = max(branch_w, 6)

    header = (
        f"  {'repo':<{name_w}}  "
        f"{'branch':<{branch_w}}  "
        f"{'dirty':>8}  "
        f"{'push':>7}  "
        f"{'pull':>7}  "
        f"{'stash':>7}  "
        f"{'last commit'}"
    )
    print(bold(header))
    print(dim("  " + "─" * (len(header) - 2)))

    for r in repos_data:
        dirty_s = fmt_status_cell(r["dirty"], "M", red)
        push_s = fmt_status_cell(r["unpushed"], "↑", yellow)
        pull_s = fmt_status_cell(r["unpulled"], "↓", cyan)
        stash_s = fmt_status_cell(r["stashes"], "S", yellow)

        branch_colored = green(r["branch"]) if r["branch"] == "main" or r["branch"] == "master" else yellow(r["branch"])

        age_str = dim(r["last_age"])

        print(
            f"  {r['name']:<{name_w}}  "
            f"{branch_colored:<{branch_w + 9}}  "  # +9 for ansi codes
            f"{dirty_s:>17}  "  # padded for ansi
            f"{push_s:>16}  "
            f"{pull_s:>16}  "
            f"{stash_s:>16}  "
            f"{age_str}"
        )

def main():
    parser = argparse.ArgumentParser(
        prog="gitlook",
        description="quick overview of all your git repos in one place"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="root directory to scan (default: current dir)"
    )
    parser.add_argument(
        "-d", "--depth",
        type=int,
        default=2,
        help="how deep to look for repos (default: 2)"
    )
    parser.add_argument(
        "-a", "--all",
        action="store_true",
        help="show clean repos too"
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="run git fetch on each repo before checking"
    )

    args = parser.parse_args()
    root = Path(args.path)

    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    print()
    print(bold(f"  scanning {root.resolve()} ..."))
    print()

    repos = find_repos(root, args.depth)

    if not repos:
        print(dim("  no git repos found"))
        sys.exit(0)

    if args.fetch:
        print(dim(f"  fetching {len(repos)} repos..."))
        for repo in repos:
            run_git(repo, "fetch", "--quiet")
        print()

    results = []
    for repo in repos:
        info = get_repo_info(repo)
        if info:
            results.append(info)

    print_table(results, show_clean=args.all)

    total = len(results)
    dirty = sum(1 for r in results if r["dirty"])
    unpushed = sum(1 for r in results if r["unpushed"])

    print()
    summary_parts = [f"{total} repos"]
    if dirty:
        summary_parts.append(red(f"{dirty} dirty"))
    if unpushed:
        summary_parts.append(yellow(f"{unpushed} unpushed"))
    if not dirty and not unpushed:
        summary_parts.append(green("all clean"))

    print(dim("  ") + " · ".join(summary_parts))
    print()

if __name__ == "__main__":
    main()
