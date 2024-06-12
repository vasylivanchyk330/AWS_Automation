# CloudFormation Stack Cleanup

This repository contains a script to delete AWS CloudFormation stacks created after a specific date-time. The script is useful for cleaning up stacks based on their creation date, with options to exclude certain stacks and force deletion without confirmation.

**The goal: automate the deletion of CloudFormation stacks created after a specific date-time.**

## Table of Contents

- [Usage](#usage)
- [Options](#options)
- [Example](#example)


## Usage

To use the script, run it from the command line with the appropriate arguments.

```sh
python delete-CF-stack-base-on-date-time.py <cutoff-date-time> [--exclude-stacks <stack1,stack2,... or exclude_stacks.txt>] [--force]
```

By defualt, the script will prompt a user confirm each stack deletion manually. Here is an example of such prompt:

```arduino
Found 2 stacks created after 2024-06-10T00:00:00Z
Are you sure you want to delete the stack stack_name1? (yes/no): yes
Initiated deletion of stack: stack_name1
Are you sure you want to delete the stack stack_name2? (yes/no): no
Skipping deletion of stack: stack_name2
```

## Arguments and Options

- `<cutoff-date-time>`: The cutoff date-time in format `YYYY-MM-DDTHH:MM:SSZ (UTC)`. Stacks created after this date-time will be deleted.
- `--exclude-stacks` or `-e`: List of stack names to exclude from deletion. This can be a comma-separated list or a path to a file containing stack names (one per line).
- `--force` or `-f`: Force deletion without confirmation. By defualt, the script will prompt a user confirm each stack deletion manually. 


## Example

- Exclude Stacks from a Comma-Separated List

  `python delete-CF-stack-base-on-date-time.py 2024-06-10T00:00:00Z --exclude-stacks stack1,stack2,stack3`

- Exclude Stacks from a File

  `python delete-CF-stack-base-on-date-time.py 2024-06-10T00:00:00Z --exclude-stacks exclude_stacks.txt`

- Forceful Deletion Without Confirmation

  `python delete-CF-stack-base-on-date-time.py 2024-06-10T00:00:00Z --exclude-stacks stack1,stack2 --force`

