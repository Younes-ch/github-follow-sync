# GitHub Follow Sync

## Purpose

This repository provides a Rich-powered console tool to help clean up your GitHub social graph. It identifies accounts you follow that don’t follow you back—often spam or bot accounts—and lets you unfollow them in bulk or selectively. It can also list users who follow you but you don’t follow back so you can follow legitimate accounts easily.

## How to use it

## Installation

```bash
pip install -r requirements.txt
```

## Usage

You need to create a [Fine-grained](https://github.com/settings/tokens?type=beta) token with the following permissions:

* Read and Write access to followers

Then create a `.env` file with the following content:

```bash
TOKEN=YOUR_TOKEN
```

Finally, run the script:

```bash
python src/main.py
```

## What’s new

This version uses the Rich library for a friendlier TUI:

* Clear intro panel and auth check
* Progress spinners while fetching followers/following
* A colorful table with numbered rows and profile links
* Choice to unfollow all, or pick specific indexes/ranges like `1-3,7,10-12`

Example selection input:

```text
1-5, 8, 11-12
```

You’ll be asked for confirmation before unfollowing all. Per-user unfollow progress is shown with a spinner and final summary.
