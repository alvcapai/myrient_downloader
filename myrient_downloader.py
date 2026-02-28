#!/usr/bin/env python3
"""
Myrient Downloader
==================
Download files from myrient.erista.me with an interactive interface.

- Asks where to save files
- Shows all categories and lets you pick which ones to download
- Preserves the full directory structure
- Resumes interrupted downloads automatically
- Downloads multiple files at the same time
- Works on Windows, macOS, and Linux

First run will automatically install required packages.
"""

import os
import sys
import time
import threading
import urllib.parse
import signal
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Version check
# ─────────────────────────────────────────────────────────────────────────────
if sys.version_info < (3, 8):
    print("ERROR: Python 3.8 or newer is required.")
    print("Please download the latest Python from https://www.python.org/downloads/")
    input("Press Enter to exit...")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Auto-install dependencies on first run
# ─────────────────────────────────────────────────────────────────────────────
_REQUIRED = {
    "requests": "requests",
    "bs4": "beautifulsoup4",
    "rich": "rich",
}

def _ensure_deps():
    missing = [pkg for mod, pkg in _REQUIRED.items()
               if __import__("importlib").util.find_spec(mod) is None]
    if not missing:
        return

    print(f"\nFirst-run setup: installing {', '.join(missing)} ...")
    print("This only happens once.\n")

    import subprocess
    for extra_args in [["--user"], []]:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet"] + extra_args + missing,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("Dependencies installed successfully!\n")
            return

    print("ERROR: Could not install required packages automatically.")
    print(f"Please run this command manually:\n")
    print(f"  pip install {' '.join(missing)}\n")
    input("Press Enter to exit...")
    sys.exit(1)

_ensure_deps()

# ─────────────────────────────────────────────────────────────────────────────
# Imports (after dependency install)
# ─────────────────────────────────────────────────────────────────────────────
import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn,
    DownloadColumn, TransferSpeedColumn, TimeRemainingColumn,
)
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.text import Text

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
BASE_URL        = "https://myrient.erista.me/files/"
CHUNK_SIZE      = 512 * 1024   # 512 KB per read chunk
MAX_RETRIES     = 3
RETRY_DELAY     = 5            # seconds between retries
REQUEST_TIMEOUT = 30           # seconds for HEAD / directory requests
STREAM_TIMEOUT  = (15, 60)     # (connect timeout, read timeout) for downloads

console = Console()

# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers
# ─────────────────────────────────────────────────────────────────────────────
def make_session() -> requests.Session:
    sess = requests.Session()
    sess.headers["User-Agent"] = (
        "MyrientDownloader/1.0 (https://github.com/)"
    )
    return sess


def fetch_directory(session: requests.Session, url: str) -> list:
    """Fetch a directory listing page and return a list of entry dicts."""
    for attempt in range(MAX_RETRIES):
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            break
        except Exception as exc:
            if attempt == MAX_RETRIES - 1:
                console.print(f"[red]  ✗ Could not fetch {url}: {exc}[/red]")
                return []
            time.sleep(RETRY_DELAY)

    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table", id="list")
    if not table:
        return []

    entries = []
    for row in table.find_all("tr"):
        link_td = row.find("td", class_="link")
        size_td = row.find("td", class_="size")
        date_td = row.find("td", class_="date")
        if not link_td:
            continue

        a = link_td.find("a")
        if not a:
            continue

        href = a.get("href", "")
        name = (a.get("title") or a.get_text(strip=True)).rstrip("/")

        # Skip navigation / sorting links
        if not href or href.startswith("?") or href.startswith("#"):
            continue
        if href in ("./", "../") or name in (".", "..") or "Parent directory" in name:
            continue

        full_url = urllib.parse.urljoin(url, href)

        # Safety: never crawl above BASE_URL
        if not full_url.startswith(BASE_URL):
            continue

        is_dir   = href.endswith("/")
        size_str = size_td.get_text(strip=True) if size_td else "-"
        date_str = date_td.get_text(strip=True) if date_td else "-"

        entries.append({
            "name":   name,
            "url":    full_url,
            "is_dir": is_dir,
            "size":   size_str,
            "date":   date_str,
        })

    return entries


def get_remote_size(session: requests.Session, url: str) -> Optional[int]:
    """Return Content-Length from a HEAD request, or None if unavailable."""
    try:
        r = session.head(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        cl = r.headers.get("Content-Length")
        return int(cl) if cl else None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Filename sanitisation (Windows compatibility)
# ─────────────────────────────────────────────────────────────────────────────
_WIN_FORBIDDEN = set('<>:"|?*')
_WIN_RESERVED  = {
    "CON", "PRN", "AUX", "NUL",
    *[f"COM{i}" for i in range(1, 10)],
    *[f"LPT{i}" for i in range(1, 10)],
}

def sanitize_name(name: str) -> str:
    """Make a filename safe on all platforms (especially Windows)."""
    if sys.platform == "win32":
        name = "".join("_" if c in _WIN_FORBIDDEN else c for c in name)
        name = name.rstrip(". ")        # Windows forbids trailing dots/spaces
        stem = name.split(".")[0].upper()
        if stem in _WIN_RESERVED:
            name = "_" + name
    return name or "_unnamed"


# ─────────────────────────────────────────────────────────────────────────────
# Download manager
# ─────────────────────────────────────────────────────────────────────────────
class DownloadManager:
    def __init__(self, dest_root: Path, workers: int = 3):
        self.dest_root   = dest_root
        self.workers     = workers
        self.session     = make_session()
        self._lock       = threading.Lock()
        self._stop       = threading.Event()
        self.stats       = dict(found=0, downloaded=0, skipped=0, failed=0, bytes_dl=0)
        self._failed: list[str] = []

    # ── Directory scanning ────────────────────────────────────────────────────

    def _scan_recursive(self, url: str, rel: Path, progress, task) -> list:
        """Recursively build a flat list of (url, relative_path) for all files."""
        files = []
        for entry in fetch_directory(self.session, url):
            if self._stop.is_set():
                break
            safe = sanitize_name(entry["name"])
            child_rel = rel / safe
            if entry["is_dir"]:
                progress.update(task, description=f"  Scanning  {str(child_rel)[:70]}")
                files.extend(self._scan_recursive(entry["url"], child_rel, progress, task))
            else:
                files.append((entry["url"], child_rel))
                with self._lock:
                    self.stats["found"] += 1
                progress.update(
                    task,
                    description=(
                        f"  [dim]Found [bold]{self.stats['found']:,}[/bold] files"
                        f" — {safe[:55]}[/dim]"
                    ),
                )
        return files

    def scan(self, categories: list) -> list:
        """Scan selected categories and return flat list of (url, rel_path)."""
        console.print("\n[bold yellow]Step 1 of 2 — Scanning directory structure[/bold yellow]")
        console.print("  [dim]This may take several minutes for large categories.[/dim]\n")

        all_files = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as prog:
            task = prog.add_task("  Scanning...", total=None)
            for cat in categories:
                prog.update(task, description=f"  Scanning [cyan]{cat['name']}[/cyan]...")
                files = self._scan_recursive(
                    cat["url"], Path(sanitize_name(cat["name"])), prog, task
                )
                all_files.extend(files)

        console.print(
            f"[green]  ✓[/green] Scan complete — "
            f"[bold]{len(all_files):,}[/bold] files found.\n"
        )
        return all_files

    # ── File download ─────────────────────────────────────────────────────────

    def _download_one(self, url: str, rel: Path, progress, overall_task) -> bool:
        """Download one file with resume and retry support. Returns True on success."""
        dest = self.dest_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        existing    = dest.stat().st_size if dest.exists() else 0
        remote_size = get_remote_size(self.session, url)

        # Skip if already complete
        if remote_size is not None and existing == remote_size:
            with self._lock:
                self.stats["skipped"] += 1
            progress.advance(overall_task)
            return True

        # Resume header if partial file exists
        headers = {"Range": f"bytes={existing}-"} if existing > 0 else {}

        file_task = progress.add_task(
            f"  [cyan]{rel.name[:60]}[/cyan]",
            total=remote_size or 0,
            completed=existing,
        )

        success = False
        for attempt in range(MAX_RETRIES):
            if self._stop.is_set():
                break
            try:
                r = self.session.get(
                    url, headers=headers, stream=True, timeout=STREAM_TIMEOUT
                )
                if r.status_code == 416:
                    # Range not satisfiable → file already complete
                    success = True
                    break
                r.raise_for_status()

                # Determine total size for the progress bar
                total = remote_size
                if total is None:
                    cl = r.headers.get("Content-Length")
                    if cl:
                        total = int(cl) + existing
                        progress.update(file_task, total=total)

                mode = "ab" if existing > 0 else "wb"
                with open(dest, mode) as fh:
                    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                        if self._stop.is_set():
                            break
                        if chunk:
                            fh.write(chunk)
                            n = len(chunk)
                            progress.advance(file_task, n)
                            with self._lock:
                                self.stats["bytes_dl"] += n

                success = not self._stop.is_set()
                break

            except Exception as exc:
                if attempt == MAX_RETRIES - 1:
                    console.log(f"[red]✗ FAILED[/red] {rel.name} — {exc}")
                    with self._lock:
                        self._failed.append(url)
                else:
                    time.sleep(RETRY_DELAY * (attempt + 1))

        progress.remove_task(file_task)
        progress.advance(overall_task)

        with self._lock:
            if success:
                self.stats["downloaded"] += 1
            else:
                self.stats["failed"] += 1

        return success

    # ── Orchestration ─────────────────────────────────────────────────────────

    def download(self, files: list):
        """Download all files concurrently."""
        console.print(
            f"[bold yellow]Step 2 of 2 — Downloading files[/bold yellow]  "
            f"[dim]({self.workers} concurrent streams)[/dim]\n"
        )

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.0f}%",
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
            refresh_per_second=4,
        ) as prog:
            overall = prog.add_task(
                "[bold green]Total progress[/bold green]",
                total=len(files),
            )

            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                futures = {
                    pool.submit(self._download_one, url, rel, prog, overall): rel
                    for url, rel in files
                }
                for fut in as_completed(futures):
                    try:
                        fut.result()
                    except Exception as e:
                        console.log(f"[red]Unexpected error: {e}[/red]")

    # ── Summary ───────────────────────────────────────────────────────────────

    def print_summary(self):
        s = self.stats
        mb = s["bytes_dl"] / (1024 * 1024)

        table = Table(
            title="Download Summary",
            header_style="bold cyan",
            show_lines=True,
        )
        table.add_column("Metric",  style="dim",   no_wrap=True)
        table.add_column("Result",  justify="right", style="bold")

        table.add_row("Files found",                  f"{s['found']:,}")
        table.add_row("Downloaded",                   f"[green]{s['downloaded']:,}[/green]")
        table.add_row("Skipped (already downloaded)", f"[yellow]{s['skipped']:,}[/yellow]")
        table.add_row("Failed",                       f"[red]{s['failed']:,}[/red]")
        table.add_row("Data transferred",             f"{mb:,.1f} MB")

        console.print()
        console.print(table)

        if self._failed:
            failed_log = self.dest_root / "failed_downloads.txt"
            failed_log.write_text("\n".join(self._failed))
            console.print(
                f"\n[red]  {len(self._failed)} file(s) failed.[/red] "
                f"URLs saved to: [dim]{failed_log}[/dim]"
            )

    def stop(self):
        self._stop.set()


# ─────────────────────────────────────────────────────────────────────────────
# Interactive prompts
# ─────────────────────────────────────────────────────────────────────────────

BANNER = r"""
  __  __ _   _ ____  ___ _____ _   _ _____
 |  \/  | | | |  _ \|_ _| ____| \ | |_   _|
 | |\/| | | | | |_) || ||  _| |  \| | | |
 | |  | | |_| |  _ < | || |___| |\  | | |
 |_|  |_|\___/|_| \_\___|_____|_| \_| |_|

        D O W N L O A D E R   v1.0
"""


def show_banner():
    console.print(Panel(BANNER, style="bold blue", border_style="bright_blue"))
    console.print(
        "[bold red]  ⚠  Myrient shuts down 31 March 2026."
        "  Download important content now![/bold red]\n"
    )


def ask_download_path() -> Path:
    default = str(Path.home() / "Downloads" / "Myrient")
    console.print("[bold]Where should the files be saved?[/bold]")
    console.print(f"  [dim]Press Enter to use the default: {default}[/dim]\n")

    raw  = Prompt.ask("  Download folder", default=default).strip()
    dest = Path(raw).expanduser().resolve()

    if not dest.exists():
        if Confirm.ask(
            f"\n  [yellow]{dest}[/yellow] does not exist. Create it?",
            default=True,
        ):
            dest.mkdir(parents=True, exist_ok=True)
        else:
            console.print("[red]  Cancelled.[/red]")
            sys.exit(0)

    console.print(f"\n  [green]✓[/green] Saving to: [bold cyan]{dest}[/bold cyan]\n")
    return dest


def ask_categories(session: requests.Session) -> list:
    console.print("[bold]Loading available categories...[/bold]")
    with console.status("  Connecting to Myrient...", spinner="dots"):
        entries = fetch_directory(session, BASE_URL)

    dirs = [e for e in entries if e["is_dir"]]
    if not dirs:
        console.print(
            "[red]  ERROR: Could not load the category list.\n"
            "  Please check your internet connection and try again.[/red]"
        )
        input("\nPress Enter to exit...")
        sys.exit(1)

    table = Table(
        title="Available Categories",
        header_style="bold magenta",
        show_lines=True,
    )
    table.add_column("#",            style="bold dim", width=4,  justify="right")
    table.add_column("Category",     style="white bold")
    table.add_column("Last Updated", style="dim")

    for i, d in enumerate(dirs, 1):
        table.add_row(str(i), d["name"], d["date"])

    console.print(table)

    console.print("\n[bold]Which categories do you want to download?[/bold]")
    console.print("  [dim]Examples:  [white]all[/white]   •   [white]1,3,5[/white]   •   [white]1-5[/white]   •   [white]2,4-7,10[/white][/dim]\n")

    while True:
        raw = Prompt.ask("  Your selection", default="all").strip().lower()

        if raw == "all":
            selected = dirs
        else:
            nums: set[int] = set()
            ok = True
            for token in raw.split(","):
                token = token.strip()
                if "-" in token:
                    parts = token.split("-", 1)
                    try:
                        lo, hi = int(parts[0].strip()), int(parts[1].strip())
                        nums.update(range(lo, hi + 1))
                    except ValueError:
                        ok = False
                        break
                else:
                    try:
                        nums.add(int(token))
                    except ValueError:
                        ok = False
                        break

            if not ok or not nums:
                console.print("  [red]Invalid input. Please try again.[/red]\n")
                continue

            bad = [n for n in nums if n < 1 or n > len(dirs)]
            if bad:
                console.print(
                    f"  [red]Numbers out of range: {bad}.  "
                    f"Choose between 1 and {len(dirs)}.[/red]\n"
                )
                continue

            selected = [dirs[n - 1] for n in sorted(nums)]

        console.print("\n  [bold green]Selected:[/bold green]")
        for d in selected:
            console.print(f"    [cyan]✓[/cyan] {d['name']}")

        if Confirm.ask("\n  Proceed with this selection?", default=True):
            return selected

        console.print()   # Let user re-select


def ask_workers() -> int:
    console.print("\n[bold]How many files to download simultaneously?[/bold]")
    console.print(
        "  [dim]More = faster downloads but uses more bandwidth.\n"
        "  Recommended: 3 for normal connections, 5+ for fast connections.[/dim]\n"
    )
    while True:
        try:
            n = IntPrompt.ask("  Concurrent downloads", default=3)
            if 1 <= n <= 20:
                return n
            console.print("  [red]Please enter a number between 1 and 20.[/red]\n")
        except Exception:
            console.print("  [red]Invalid input. Please enter a number.[/red]\n")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    show_banner()

    session  = make_session()
    dest     = ask_download_path()
    selected = ask_categories(session)
    workers  = ask_workers()

    console.print("\n[bold]Ready to start:[/bold]")
    console.print(f"  Destination  : [cyan]{dest}[/cyan]")
    console.print(f"  Categories   : {len(selected)} selected")
    console.print(f"  Concurrency  : {workers} simultaneous downloads")

    if not Confirm.ask("\n[bold yellow]  Start downloading now?[/bold yellow]", default=True):
        console.print("[red]  Cancelled.[/red]")
        sys.exit(0)

    manager = DownloadManager(dest, workers=workers)

    # Handle Ctrl+C gracefully
    def _on_interrupt(sig, frame):
        console.print(
            "\n\n[yellow]  Interrupted by user. "
            "Finishing active downloads, please wait...[/yellow]"
        )
        manager.stop()

    signal.signal(signal.SIGINT, _on_interrupt)

    console.print()

    # Phase 1: scan
    files = manager.scan(selected)
    if not files:
        console.print("[red]  No files found to download. Exiting.[/red]")
        input("\nPress Enter to exit...")
        sys.exit(0)

    # Phase 2: download
    manager.download(files)
    manager.print_summary()

    console.print(f"\n[bold green]  Done![/bold green]  Files saved to:[/bold green]")
    console.print(f"  [cyan]{dest}[/cyan]\n")

    # Keep the window open on double-click (Windows / macOS)
    if sys.platform in ("win32", "darwin"):
        input("Press Enter to close this window...")


if __name__ == "__main__":
    main()
