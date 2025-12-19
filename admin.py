#!/usr/bin/env python3
"""
Admin CLI for Knee MRI Segmentation Pipeline

Usage:
    python admin.py emails              List all user emails
    python admin.py emails --csv        Export emails as CSV
    python admin.py stats               Show usage statistics
    python admin.py stats --json        Output stats as JSON
    python admin.py times               Show processing time history
    python admin.py jobs                List jobs with research consent
    python admin.py jobs --all          List all jobs
    python admin.py jobs --json         Export jobs as JSON
    python admin.py results             List saved results on disk

Examples:
    python admin.py emails --csv > emails.csv
    python admin.py stats
    python admin.py jobs --all --json > all_jobs.json
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import redis

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.statistics import get_all_user_emails, get_statistics
from backend.config import get_settings


def get_redis():
    """Get Redis client using application settings."""
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


def cmd_emails(args):
    """List all user email addresses."""
    r = get_redis()
    emails = get_all_user_emails(r)
    emails = sorted(emails)

    if args.csv:
        print("email")
        for email in emails:
            print(email)
    else:
        print(f"{'=' * 50}")
        print(f"  User Emails ({len(emails)} total)")
        print(f"{'=' * 50}")
        print()
        for email in emails:
            print(f"  {email}")
        print()


def cmd_stats(args):
    """Show usage statistics."""
    r = get_redis()
    stats = get_statistics(r)

    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        print(f"{'=' * 50}")
        print("  Usage Statistics")
        print(f"{'=' * 50}")
        print()
        print(f"  Total jobs processed:  {stats['total_processed']}")
        print(f"  Jobs today:            {stats['today_processed']}")
        print(f"  Unique users:          {stats['unique_users']}")
        print(f"  Avg processing time:   {stats['avg_processing_time']}s ({stats['avg_processing_time']/60:.1f} min)")
        print(f"  Uptime:                {stats['uptime_hours']} hours")
        print()


def cmd_times(args):
    """Show processing time history."""
    r = get_redis()
    times = r.lrange("processing_times", 0, -1)

    if args.json:
        times_data = [float(t) for t in times]
        avg = sum(times_data) / len(times_data) if times_data else 0
        print(json.dumps({
            "count": len(times_data),
            "times_seconds": times_data,
            "average_seconds": avg,
            "average_minutes": avg / 60
        }, indent=2))
    else:
        print(f"{'=' * 50}")
        print(f"  Processing Times (last {len(times)} jobs)")
        print(f"{'=' * 50}")
        print()

        if not times:
            print("  No processing times recorded yet.")
            print()
            return

        print(f"  {'#':>3}  {'Seconds':>10}  {'Minutes':>10}")
        print(f"  {'-' * 3}  {'-' * 10}  {'-' * 10}")

        for i, t in enumerate(times, 1):
            secs = float(t)
            print(f"  {i:>3}  {secs:>10.1f}  {secs/60:>10.1f}")

        avg = sum(float(t) for t in times) / len(times)
        print()
        print(f"  Average: {avg:.1f}s ({avg/60:.1f} min)")
        print()


def cmd_jobs(args):
    """List jobs (optionally filtered by research consent)."""
    r = get_redis()
    jobs_data = r.hgetall("jobs")

    jobs = []
    for job_id, job_json in jobs_data.items():
        job = json.loads(job_json)
        if args.all or job.get("retain_for_research", False):
            jobs.append(job)

    # Sort by created_at (newest first)
    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)

    if args.json:
        print(json.dumps(jobs, indent=2))
        return

    filter_msg = "All Jobs" if args.all else "Jobs with Research Consent"
    print(f"{'=' * 80}")
    print(f"  {filter_msg} ({len(jobs)} total)")
    print(f"{'=' * 80}")
    print()

    if not jobs:
        print("  No jobs found.")
        print()
        return

    # Header
    print(f"  {'ID':<10}  {'Status':<10}  {'Retain':^6}  {'Created':<20}  {'Filename'}")
    print(f"  {'-' * 10}  {'-' * 10}  {'-' * 6}  {'-' * 20}  {'-' * 30}")

    for job in jobs:
        job_id = job.get("id", "unknown")[:8] + "..."
        status = job.get("status", "unknown")
        filename = job.get("input_filename", "N/A")
        created = job.get("created_at", "")[:19]  # Trim microseconds
        retain = "✓" if job.get("retain_for_research") else "✗"
        email = job.get("email", "")

        print(f"  {job_id:<10}  {status:<10}  {retain:^6}  {created:<20}  {filename}")
        if email and args.verbose:
            print(f"              └─ email: {email}")

    print()

    # Summary
    retained_count = sum(1 for j in jobs if j.get("retain_for_research"))
    complete_count = sum(1 for j in jobs if j.get("status") == "complete")
    error_count = sum(1 for j in jobs if j.get("status") == "error")

    print(f"  Summary: {complete_count} complete, {error_count} errors, {retained_count} with research consent")
    print()


def cmd_results(args):
    """List saved results on disk."""
    settings = get_settings()
    results_dir = settings.results_dir

    if not results_dir.exists():
        print(f"Results directory does not exist: {results_dir}")
        return

    print(f"{'=' * 80}")
    print(f"  Saved Results ({results_dir})")
    print(f"{'=' * 80}")
    print()

    job_dirs = sorted(results_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)

    if not job_dirs:
        print("  No results found.")
        print()
        return

    total_size = 0
    for job_dir in job_dirs:
        if not job_dir.is_dir():
            continue

        # Get job ID
        job_id = job_dir.name[:8] + "..."

        # Check for results zip
        zip_files = list(job_dir.glob("*_results.zip"))
        zip_name = zip_files[0].name if zip_files else "-"
        zip_size = zip_files[0].stat().st_size if zip_files else 0
        total_size += zip_size

        # Get modification time
        mtime = datetime.fromtimestamp(job_dir.stat().st_mtime)
        mtime_str = mtime.strftime("%Y-%m-%d %H:%M")

        # Check for pipeline output
        has_output = (job_dir / "pipeline_output").exists()
        output_marker = "✓" if has_output else "-"

        size_mb = zip_size / (1024 * 1024)
        print(f"  {job_id}  {mtime_str}  {size_mb:>6.1f} MB  {output_marker}  {zip_name}")

    print()
    print(f"  Total: {len(job_dirs)} results, {total_size / (1024 * 1024):.1f} MB")
    print()


def cmd_job_detail(args):
    """Show detailed info for a specific job."""
    r = get_redis()

    # Try to find job by partial ID
    jobs_data = r.hgetall("jobs")
    matching_jobs = []

    for job_id, job_json in jobs_data.items():
        if job_id.startswith(args.job_id) or args.job_id in job_id:
            matching_jobs.append(json.loads(job_json))

    if not matching_jobs:
        print(f"No job found matching: {args.job_id}")
        return

    if len(matching_jobs) > 1:
        print(f"Multiple jobs match '{args.job_id}':")
        for job in matching_jobs:
            print(f"  {job['id']}")
        return

    job = matching_jobs[0]

    if args.json:
        print(json.dumps(job, indent=2))
        return

    print(f"{'=' * 60}")
    print(f"  Job Details: {job['id']}")
    print(f"{'=' * 60}")
    print()
    print(f"  Status:           {job.get('status')}")
    print(f"  Input file:       {job.get('input_filename')}")
    print(f"  Input path:       {job.get('input_path')}")
    print(f"  Research consent: {'Yes' if job.get('retain_for_research') else 'No'}")
    print(f"  Email:            {job.get('email') or '-'}")
    print()
    print(f"  Created:          {job.get('created_at')}")
    print(f"  Started:          {job.get('started_at') or '-'}")
    print(f"  Completed:        {job.get('completed_at') or '-'}")
    print()

    if job.get("status") == "complete":
        print(f"  Result path:      {job.get('result_path')}")
        size_bytes = job.get('result_size_bytes', 0)
        print(f"  Result size:      {size_bytes / (1024*1024):.1f} MB")

    if job.get("status") == "error":
        print(f"  Error code:       {job.get('error_code')}")
        print(f"  Error message:    {job.get('error_message')}")

    print()
    print("  Options:")
    for key, value in job.get("options", {}).items():
        print(f"    {key}: {value}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Admin CLI for Knee MRI Segmentation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python admin.py emails              # List all user emails
  python admin.py emails --csv        # Export as CSV
  python admin.py stats               # Show statistics
  python admin.py times               # Show processing times
  python admin.py jobs                # Jobs with research consent
  python admin.py jobs --all          # All jobs
  python admin.py results             # List saved results
  python admin.py job abc123          # Show specific job details
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # emails command
    emails_parser = subparsers.add_parser("emails", help="List all user email addresses")
    emails_parser.add_argument("--csv", action="store_true", help="Output as CSV")

    # stats command
    stats_parser = subparsers.add_parser("stats", help="Show usage statistics")
    stats_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # times command
    times_parser = subparsers.add_parser("times", help="Show processing time history")
    times_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # jobs command
    jobs_parser = subparsers.add_parser("jobs", help="List jobs")
    jobs_parser.add_argument("--all", action="store_true", help="Show all jobs, not just research-consented")
    jobs_parser.add_argument("--json", action="store_true", help="Output as JSON")
    jobs_parser.add_argument("-v", "--verbose", action="store_true", help="Show additional details like email")

    # results command
    results_parser = subparsers.add_parser("results", help="List saved results on disk")

    # job (single job detail) command
    job_parser = subparsers.add_parser("job", help="Show details for a specific job")
    job_parser.add_argument("job_id", help="Job ID (or partial ID)")
    job_parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    commands = {
        "emails": cmd_emails,
        "stats": cmd_stats,
        "times": cmd_times,
        "jobs": cmd_jobs,
        "results": cmd_results,
        "job": cmd_job_detail,
    }

    if args.command in commands:
        try:
            commands[args.command](args)
        except redis.ConnectionError:
            print("Error: Cannot connect to Redis. Is it running?")
            print("  Try: make redis-start (development) or check Docker (production)")
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

