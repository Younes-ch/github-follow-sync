from __future__ import annotations

import os
import sys
from typing import Iterable, List, Dict

from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

from helpers import send_get_request, send_delete_request, send_put_request


API_VERSION = "2022-11-28"
PER_PAGE = 100

console = Console()


def require_token() -> str:
    load_dotenv()
    token = os.getenv("TOKEN")
    if not token:
        console.print("❌ [bold red]TOKEN not found[/]. Create a .env with TOKEN=your_pat", style="red")
        sys.exit(1)
    return token


def auth_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": API_VERSION,
        "Accept": "application/vnd.github+json",
    }


def iter_paginated(url: str, headers: Dict[str, str]) -> Iterable[Dict]:
    """Iterate all pages for a GitHub collection endpoint.
    Assumes per_page set in URL. Follows Link rel=next until exhausted.
    """
    page = 1
    next_url = url
    while next_url:
        resp = send_get_request(next_url, headers=headers)
        if resp.status_code == 401:
            console.print("❌ [bold red]Invalid token or insufficient scopes.[/]")
            sys.exit(1)
        if resp.status_code >= 400:
            console.print(f"❌ [bold red]GitHub API error {resp.status_code}[/]: {resp.text}")
            sys.exit(1)

        data = resp.json() or []
        for item in data:
            yield item

        # pagination via Link header
        link = resp.headers.get("Link", "")
        next_url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip().strip("<>")
                break
        page += 1


def fetch_usernames(endpoint: str, token: str) -> List[str]:
    headers = auth_headers(token)
    url = f"{endpoint}?per_page={PER_PAGE}&page=1"
    usernames: List[str] = []
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True, console=console) as progress:
        task = progress.add_task("📥 Fetching from GitHub...", start=True)
        for item in iter_paginated(url, headers):
            if "login" in item:
                usernames.append(item["login"])
        progress.update(task, description=f"✅ Fetched {len(usernames)} users")
    return usernames


def render_intro():
    title = Text.from_markup("[bold cyan]🔄 GitHub Follow Sync[/]")
    subtitle = Text.from_markup("[dim]🧹 Unfollow non-followers, 🤝 follow back your supporters[/]")
    panel = Panel(Align.center(Text.assemble(title, "\n", subtitle), vertical="middle"), style="bold white", expand=False)
    console.print(panel)


def show_table(users: List[str], title: str):
    table = Table(title=title, box=box.SIMPLE_HEAVY)
    table.add_column("#", style="dim", width=4)
    table.add_column("Username", style="cyan", no_wrap=True)
    table.add_column("Profile", style="magenta")
    for idx, user in enumerate(users, start=1):
        table.add_row(str(idx), user, f"https://github.com/{user}")
    console.print(table)


def batch_unfollow(users: List[str], token: str):
    headers = auth_headers(token)
    successes = 0
    failures = 0
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=False, console=console) as progress:
        task = progress.add_task("🧹 Unfollowing...", total=len(users))
        for user in users:
            resp = send_delete_request(f"https://api.github.com/user/following/{user}", headers)
            if resp.status_code == 204:
                successes += 1
            else:
                failures += 1
            progress.advance(task)
    console.print(f"✅ [green]Unfollowed {successes}[/] • ❌ [red]failed {failures}[/]")


def batch_follow(users: List[str], token: str):
    headers = auth_headers(token)
    successes = 0
    failures = 0
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=False, console=console) as progress:
        task = progress.add_task("➕ Following...", total=len(users))
        for user in users:
            resp = send_put_request(f"https://api.github.com/user/following/{user}", headers)
            if resp.status_code in (204, 200):
                successes += 1
            else:
                failures += 1
            progress.advance(task)
    console.print(f"✅ [green]Followed {successes}[/] • ❌ [red]failed {failures}[/]")


def main():
    render_intro()
    token = require_token()
    headers = auth_headers(token)

    # Pre-flight check
    ping = send_get_request("https://api.github.com/user", headers)
    if ping.status_code == 200:
        me = ping.json().get("login", "you")
        console.print(f"🔐 Authenticated as [bold]{me}[/]\n")
    elif ping.status_code == 401:
        console.print("❌ [bold red]Invalid token.[/]")
        sys.exit(1)
    else:
        console.print(f"⚠️ [yellow]Warning:[/] GitHub returned {ping.status_code}")

    following = fetch_usernames("https://api.github.com/user/following", token)
    followers = fetch_usernames("https://api.github.com/user/followers", token)

    not_following_me_back = [u for u in following if u not in followers]
    not_followed_by_me = [u for u in followers if u not in following]

    if not not_following_me_back and not not_followed_by_me:
        console.print("🎉 [bold green]You and your followers are in perfect sync![/]")
        return

    # Menu
    console.rule("📋 Menu")
    options = []
    idx = 1
    if not_following_me_back:
        console.print(f"{idx}) 🚫 Show and optionally unfollow users who don't follow you back [{len(not_following_me_back)}]")
        options.append("unfollow")
        idx += 1
    if not_not_followed := bool(not not_followed_by_me):
        pass
    if not_followed_by_me:
        console.print(f"{idx}) ➕ Show and optionally follow users you don't follow back [{len(not_followed_by_me)}]")
        options.append("follow")
        idx += 1
    console.print(f"{idx}) 🚪 Exit")
    options.append("exit")

    choice = Prompt.ask("Choose an option", choices=[str(i) for i in range(1, len(options) + 1)], default=str(len(options)))
    chosen = options[int(choice) - 1]

    def pick_and_apply(users: List[str], action_label: str, apply_fn):
        emoji = "🚫" if action_label == "Unfollow" else ("➕" if action_label == "Follow" else "")
        show_table(users, title=f"{emoji} {action_label} candidates ({len(users)})")
        if not Confirm.ask(f"Do you want to {action_label.lower()} some or all of them?", default=False):
            return
        mode = Prompt.ask(f"Choose mode: 1) {emoji} {action_label} all  2) 🎯 Pick by index range", choices=["1", "2"], default="2")
        if mode == "1":
            if Confirm.ask(f"Are you sure you want to {action_label.lower()} ALL listed users? {emoji}", default=False):
                apply_fn(users, token)
            return
        console.print(f"🎯 Enter indexes to {action_label.lower()} (e.g. 1-3,5,8). Press Enter to cancel.")
        raw = console.input("> ").strip()
        if not raw:
            console.print("[dim]🛑 No selection.[/]")
            return
        selected: List[int] = []
        for part in raw.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-", 1)
                if a.isdigit() and b.isdigit():
                    start, end = int(a), int(b)
                    if start <= end:
                        selected.extend(range(start, end + 1))
            elif part.isdigit():
                selected.append(int(part))
        selected = sorted(set(i for i in selected if 1 <= i <= len(users)))
        chosen_users = [users[i - 1] for i in selected]
        if not chosen_users:
            console.print("[dim]🛑 No valid indexes selected.[/]")
            return
        console.print(f"{emoji} {action_label} {len(chosen_users)} users...")
        apply_fn(chosen_users, token)

    if chosen == "unfollow":
        pick_and_apply(not_following_me_back, "Unfollow", batch_unfollow)
    elif chosen == "follow":
        pick_and_apply(not_followed_by_me, "Follow", batch_follow)
    else:
        return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/]")




