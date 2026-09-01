"""
Test: Search LinkedIn for Cloud Engineering jobs in Oregon using DOM extractor.
"""
import httpx
import time

BRIDGE = "http://127.0.0.1:8765"
JOBS_URL = "https://www.linkedin.com/jobs/search/?keywords=cloud+engineering&location=Oregon%2C+United+States"


def command(action: str, params: dict = {}) -> dict:
    r = httpx.post(f"{BRIDGE}/command", json={"action": action, "params": params}, timeout=30)
    r.raise_for_status()
    return r.json()


def check_health():
    r = httpx.get(f"{BRIDGE}/health", timeout=5)
    data = r.json()
    if not data.get("extension_connected"):
        raise RuntimeError("Extension is not connected. Make sure Chromium is open with the extension loaded.")
    print("Bridge: OK | Extension: Connected\n")


def main():
    print("=== Persia — LinkedIn Job Search Test ===\n")
    check_health()

    print("Navigating to LinkedIn Jobs: cloud engineering in Oregon...")
    result = command("navigate_to", {"url": JOBS_URL})
    if result.get("error"):
        raise RuntimeError(f"Navigation failed: {result['error']}")

    print("Waiting for page to render...")
    time.sleep(6)

    print("Extracting job listings via DOM extractor...\n")
    result = command("search_jobs")

    if result.get("error"):
        raise RuntimeError(f"Extractor failed: {result['error']}")

    data = result.get("data", {})

    if data.get("error"):
        print(f"Extractor reported: {data['error']}")
        return

    jobs = data.get("jobs", [])
    total = data.get("total_on_page", 0)

    print(f"Total job cards on page: {total}")
    print(f"Returning top {min(5, len(jobs))} jobs:\n")

    for idx, job in enumerate(jobs[:5], 1):
        print(f"  {idx}. {job['title']}")
        print(f"     Company:  {job['company']}")
        print(f"     Location: {job['location']}")
        if job.get("url"):
            print(f"     URL:      {job['url'].split('?')[0]}")
        print()


if __name__ == "__main__":
    main()
