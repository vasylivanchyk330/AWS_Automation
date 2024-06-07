import subprocess
import time
import argparse
from datetime import datetime
import logging
import os

def setup_logger(log_file):
    """Setup logger to log messages to both console and file."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create handlers
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(log_file)

    # Create formatters and add them to the handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

def log_unique_lines(log_func, message):
    """Log each line in the message uniquely."""
    seen_lines = set()
    for line in message.splitlines():
        if line not in seen_lines:
            log_func(line)
            seen_lines.add(line)

def run_script(script_path, script_args):
    """Run a script with arguments and wait for it to finish."""
    try:
        result = subprocess.run(["python", script_path] + script_args, check=True, capture_output=True, text=True)
        logging.info(f"Output of {script_path}:\n")
        if result.stdout:
            log_unique_lines(logging.info, result.stdout)
        if result.stderr:
            log_unique_lines(logging.info, result.stderr)
    except subprocess.CalledProcessError as e:
        if e.stdout:
            log_unique_lines(logging.error, e.stdout)
        if e.stderr:
            log_unique_lines(logging.error, e.stderr)

def main(bucket_names, wait_time, log_file):
    # Setup logger
    setup_logger(log_file)

    # List of scripts to run in the given order with their respective arguments
    scripts = [
        ("add-deny-policy/add-bucket-policy.py", bucket_names + ["add-deny-policy/deny-bucket-policy-template.json"]),
        ("set-lifecycle-rule/set-lifecycle-rule.py", bucket_names + ["set-lifecycle-rule/lifecycle-policy-01.json", "set-lifecycle-rule/lifecycle-policy-02.json"]),
        ("bucket-content-cleanup/delete-s3-bucket-objects-versions-markers.py", bucket_names),
        ("delete-failed-multipart-uploads/delete-failed-multipart-uploads.py", bucket_names),
        ("delete-bucket/delete-bucket.py", bucket_names)
    ]

    for script_path, script_args in scripts:
        logging.info(f"STARTING SCRIPT RUN -- {script_path}")
        logging.info(f"Running {script_path} with arguments {script_args}...")
        run_script(script_path, script_args)
        logging.info(f"Finished running {script_path}.\n")

        # If the current script is the lifecycle rule script, wait for the specified time
        if script_path == "set-lifecycle-rule/set-lifecycle-rule.py" and wait_time > 0:
            logging.info(f"Waiting for {wait_time} minutes before proceeding to the next script...")
            time.sleep(wait_time * 60)  # Convert minutes to seconds

    # Print out the log file location at the end
    print(f"THE LOG FILE LOCATION IS: {log_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a series of S3 bucket management scripts.")
    parser.add_argument("buckets", nargs="+", help="Names of the S3 buckets")
    parser.add_argument("--lifecycle-rules-wait", "-w", type=int, default=0, help="Minutes to wait after setting lifecycle rules")
    parser.add_argument("--log-file", "-l", type=str, help="Log file to store the output")

    args = parser.parse_args()

    bucket_names = args.buckets
    wait_time = args.lifecycle_rules_wait

    # Define the default log file path
    log_dir = "./.script-logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = args.log_file or os.path.join(log_dir, f"script_run_{datetime.now().strftime('%Y_%m_%d___%H%M%S')}.log")

    main(bucket_names, wait_time, log_file)

