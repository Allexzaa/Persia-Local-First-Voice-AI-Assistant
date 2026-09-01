"""
Test: Search LinkedIn for Cloud Engineering jobs in Oregon, then fetch
description for the first 2 results.
"""
import httpx, time

BRIDGE = "http://127.0.0.1:8765"
JOBS_URL = "https://www.linkedin.com/jobs/search/?keywords=cloud+engineering&location=Oregon%2C+United+States"

def command(action, params={}):
    r = httpx.post(f"{BRIDGE}/command", json={"action": action, "params": params}, timeout=30)
    r.raise_for_status()
    return r.json()

def check_health():
    r = httpx.get(f"{BRIDGE}/health", timeout=5)
    if not r.json().get("extension_connected"):
        raise RuntimeError("Extension not connected.")
    print("Bridge: OK | Extension: Connected\n")

def main():
    print("=== Persia — LinkedIn Job Details Test ===\n")
    check_health()

    print("Navigating to LinkedIn Jobs...")
    command("navigate_to", {"url": JOBS_URL})
    time.sleep(6)

    print("Fetching job list...\n")
    result = command("search_jobs")
    jobs = result.get("data", {}).get("jobs", [])
    if not jobs:
        print("No jobs found.")
        return

    # Only test first 2 jobs
    for idx, job in enumerate(jobs[:2], 1):
        print(f"--- Job {idx} ---")
        print(f"Title:   {job['title']}")
        print(f"Company: {job['company']}")
        print(f"Location:{job['location']}")
        print(f"Job ID:  {job['job_id']}")
        print()

        print(f"Fetching description for job {idx}...")
        detail = command("get_job_details", {"job_id": job["job_id"]})
        data = detail.get("data", {})

        if data.get("error"):
            print(f"Error: {data['error']}\n")
            continue

        desc = data.get("description", "")
        print(f"Description ({len(desc)} chars):\n")
        print(desc[:2000])
        print("\n" + "="*60 + "\n")
        time.sleep(2)

if __name__ == "__main__":
    main()
