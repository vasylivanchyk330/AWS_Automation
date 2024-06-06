import subprocess

# List of scripts to run in the given order
scripts = [
    "add-deny-policy/add-bucket-policy.py",
    "set-lifecycle-rule/set-lifecycle-rule.py",
    "bucket-content-cleanup/delete-s3-bucket-objects-versions-markers.py",
    "delete-failed-multipart-uploads/delete-failed-multipart-uploads.py",
    "delete-bucket/delete-bucket.py"
]

def run_script(script_path):
    """Run a script and wait for it to finish."""
    try:
        result = subprocess.run(["python", script_path], check=True, capture_output=True, text=True)
        print(f"Output of {script_path}:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_path}:\n{e.stderr}")

def main():
    for script in scripts:
        print(f"Running {script}...")
        run_script(script)
        print(f"Finished running {script}.\n")

if __name__ == "__main__":
    main()