import subprocess
import sys
import time
import argparse

def run_script(script_path, script_args, log_file):
    """Run a script with arguments and wait for it to finish."""
    try:
        result = subprocess.run(["python", script_path] + script_args, check=True, capture_output=True, text=True)
        with open(log_file, 'a') as log:
            log.write(f"Output of {script_path}:\n{result.stdout}\n")
    except subprocess.CalledProcessError as e:
        with open(log_file, 'a') as log:
            log.write(f"Error running {script_path}:\n{e.stderr}\n")

def main(bucket_names, wait_time, log_file):
    # List of scripts to run in the given order with their respective arguments
    scripts = [
        ("add-deny-policy/add-bucket-policy.py", ["add-deny-policy/deny-bucket-policy-template.json"]),
        ("set-lifecycle-rule/set-lifecycle-rule.py", ["set-lifecycle-rule/lifecycle-policy-01.json", "set-lifecycle-rule/lifecycle-policy-02.json"]),
        ("bucket-content-cleanup/delete-s3-bucket-objects-versions-markers.py", bucket_names),
        ("delete-failed-multipart-uploads/delete-failed-multipart-uploads.py", bucket_names),
        ("delete-bucket/delete-bucket.py", bucket_names)
    ]

    for script_path, script_args in scripts:
        print(f"Running {script_path} with arguments {script_args}...")
        run_script(script_path, script_args, log_file)
        print(f"Finished running {script_path}.\n")

        # If the current script is the lifecycle rule script, wait for the specified time
        if script_path == "set-lifecycle-rule/set-lifecycle-rule.py" and wait_time > 0:
            print(f"Waiting for {wait_time} minutes before proceeding to the next script...")
            time.sleep(wait_time * 60)  # Convert minutes to seconds

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a series of S3 bucket management scripts.")
    parser.add_argument("buckets", nargs="+", help="Names of the S3 buckets")
    parser.add_argument("--lifecycle-rules-wait", "-w", type=int, default=0, help="Minutes to wait after setting lifecycle rules")
    parser.add_argument("--log-file", "-l", type=str, default="script.log", help="Log file to store the output")

    args = parser.parse_args()

    bucket_names = args.buckets
    wait_time = args.lifecycle_rules_wait
    log_file = args.log_file

    main(bucket_names, wait_time, log_file)
