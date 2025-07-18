#! usr/bin/env sh

# This file is just included in the repo because I don't write many shell
# scripts and I spent some time on this one before switching the implementation
# to python

# -e if any command in this script fails, stop running the script. Note: you can get around this by using || after the command that could fail.
# -u referencing an undefined variable is an error. Note: you can get around this with a substitution. For example: "${x:-}".
# -o pipefail causes sequences of pipes to terminate if any part of the pipe returns a nonzero exit code.
set -euo pipefail


if ! command -v git >/dev/null 2>&1; then
  echo "Error: git not found on path" >&2
  exit 1
fi

if ! command -v cloc >/dev/null 2>&1; then
  echo "Error: cloc not found on path" >&2
  exit 1
fi

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
default_output_file="$SCRIPT_DIR/cloc_history.txt"
output_file=$(echo $1 || echo $default_output_file)
separator="%%%%%%" # separates the cloc results for different hashes in the output file

rm "$default_output_file" &> /dev/null || :

current_branch_name=$(git rev-parse --abbrev-ref HEAD)

num_commits_in_current_branch=$(git rev-list --count HEAD)
num_commits_in_current_branch=59

echo "Counting lines in $num_commits_in_current_branch commits in $current_branch_name"

count_lines_in_commit () {
  local hash
  local commit_time_iso

  hash="$1"
  git checkout "$hash" &> /dev/null
  commit_time_iso=$(git --no-pager show -s --format=%cI HEAD)

  echo "Counting lines in commit hash $hash..."
  echo "$separator" >> "$output_file"
  echo "$hash" >> "$output_file"
  echo "$commit_time_iso" >> "$output_file"
  cloc . --VCS=git >> "$output_file"
}

# Define cleanup function
cleanup() {
  echo "\nReceived signal to end, cleaning up..."
  rm "$output_file"
  git checkout "$current_branch_name" &> /dev/null
  echo done.
}

# Trap signals: SIGINT (Ctrl+C), SIGTERM (kill), and EXIT
trap cleanup INT TERM

commit_hashes=$(git rev-list --no-abbrev-commit --reverse HEAD)

printf '%s\n' "$commit_hashes" | while IFS= read -r hash; do
  count_lines_in_commit "$hash"
done

echo done
