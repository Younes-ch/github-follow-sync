from __future__ import annotations

import os
import sys
from typing import Iterable, List, Dict

from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

import questionary

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


def batch_unfollow(users: List[str], token: str) -> List[str]:
    headers = auth_headers(token)
    successes = 0
    failures = 0
    success_users: List[str] = []
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=False, console=console) as progress:
        task = progress.add_task("🧹 Unfollowing...", total=len(users))
        for user in users:
            resp = send_delete_request(f"https://api.github.com/user/following/{user}", headers)
            if resp.status_code == 204:
                successes += 1
                success_users.append(user)
            else:
                failures += 1
            progress.advance(task)
    console.print(f"✅ [green]Unfollowed {successes}[/] • ❌ [red]failed {failures}[/]")
    return success_users


def batch_follow(users: List[str], token: str) -> List[str]:
    headers = auth_headers(token)
    successes = 0
    failures = 0
    success_users: List[str] = []
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=False, console=console) as progress:
        task = progress.add_task("➕ Following...", total=len(users))
        for user in users:
            resp = send_put_request(f"https://api.github.com/user/following/{user}", headers)
            if resp.status_code in (204, 200):
                successes += 1
                success_users.append(user)
            else:
                failures += 1
            progress.advance(task)
    console.print(f"✅ [green]Followed {successes}[/] • ❌ [red]failed {failures}[/]")
    return success_users


def main():
    render_intro()
    token = require_token()
    headers = auth_headers(token)

    ping = send_get_request("https://api.github.com/user", headers)
    if ping.status_code == 200:
        me = ping.json().get("login", "you")
        console.print(f"🔐 Authenticated as [bold]{me}[/]\n")
    elif ping.status_code == 401:
        console.print("❌ [bold red]Invalid token.[/]")
        sys.exit(1)
    else:
        console.print(f"⚠️ [yellow]Warning:[/] GitHub returned {ping.status_code}")

    def pick_and_apply(users: List[str], action_label: str, apply_fn) -> List[str]:
        emoji = "🚫" if action_label == "Unfollow" else ("➕" if action_label == "Follow" else "")
        show_table(users, title=f"{emoji} {action_label} candidates ({len(users)})")
        decision = questionary.select(
            message="How do you want to proceed?",
            choices=[
                questionary.Choice(title=f"{emoji} {action_label} ALL listed users", value="all"),
                questionary.Choice(title="🎯 Pick users", value="pick"),
                questionary.Choice(title="🛑 Cancel", value="cancel"),
            ],
        ).ask()
        if decision == "cancel":
            console.print("[dim]🛑 Cancelled.[/]")
            return []
        if decision == "all":
            return apply_fn(users, token)
        picked = questionary.checkbox(
            message=f"Select users to {action_label.lower()}",
            choices=[questionary.Choice(title=u, value=u) for u in users],
            validate=lambda sel: True if len(sel) > 0 else "Select at least one user or choose Cancel",
        ).ask()
        if not picked:
            console.print("[dim]🛑 No selection.[/]")
            return []
        chosen_users = list(picked)
        console.print(f"{emoji} {action_label} {len(chosen_users)} users...")
        return apply_fn(chosen_users, token)

    following = fetch_usernames("https://api.github.com/user/following", token)
    followers = fetch_usernames("https://api.github.com/user/followers", token)
    not_following_me_back = [u for u in following if u not in followers]
    not_followed_by_me = [u for u in followers if u not in following]

    while True:
        if not not_following_me_back and not not_followed_by_me:
            console.print("🎉 [bold green]You and your followers are in perfect sync![/]")
            break
        console.rule("📋 Menu")
        menu_choices = []
        if not_following_me_back:
            menu_choices.append(questionary.Choice(
                title=f"🚫 Unfollow {len(not_following_me_back)} {'user' if len(not_following_me_back)==1 else 'users'} who don't follow you back",
                value="unfollow",
            ))
        if not_followed_by_me:
            menu_choices.append(questionary.Choice(
                title=f"➕ Follow {len(not_followed_by_me)} {'user' if len(not_followed_by_me)==1 else 'users'} you don't follow back",
                value="follow",
            ))
        menu_choices.append(questionary.Choice(title="🚪 Exit", value="exit"))
        chosen = questionary.select(
            message="Choose an option",
            choices=menu_choices,
        ).ask()
        if chosen == "unfollow":
            success = pick_and_apply(not_following_me_back, "Unfollow", batch_unfollow)
            if success:
                success_set = set(success)
                not_following_me_back = [u for u in not_following_me_back if u not in success_set]
                following = [u for u in following if u not in success_set]
            continue
        if chosen == "follow":
            success = pick_and_apply(not_followed_by_me, "Follow", batch_follow)
            if success:
                success_set = set(success)
                not_followed_by_me = [u for u in not_followed_by_me if u not in success_set]
                for u in success:
                    if u not in following:
                        following.append(u)
            continue
        break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/]")




