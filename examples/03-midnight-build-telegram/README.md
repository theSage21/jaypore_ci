# Midnight Build with Telegram Notifications

Schedule a nightly build at midnight and push pass/fail status to a Telegram
chat.

## How it works

The file `.jci/crontab` contains a single cron entry:

```
0 0 * * * run
```

This tells Jaypore CI to execute `.jci/run.sh` every day at midnight.

To install (or update) this schedule into the system crontab, run:

```bash
git jci cron sync
```

`cron sync` reads `.jci/crontab`, translates each line into a real crontab
entry that invokes `git jci run` inside the repository, and writes it to the
current user's crontab. Run the command again after changing `.jci/crontab` to
pick up new schedules.

## Setting up Telegram

1. Create a bot via [BotFather](https://t.me/BotFather) and note the **bot
   token**.
2. Get your **chat ID** by sending a message to the bot and visiting
   `https://api.telegram.org/bot<TOKEN>/getUpdates`.
3. Export both values so Jaypore CI can see them at runtime:

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
export TELEGRAM_CHAT_ID="-100..."
```

You can persist these in `~/.bashrc`, a `.env` file sourced by your shell, or
whatever secrets mechanism you prefer.

## What the build does

1. `cd` into the repo root.
2. Run `python3 manage.py test core` and capture the exit code.
3. Save test output and exit code to `$JCI_OUTPUT_DIR`.
4. Send a Telegram message with the repo name, short commit hash, pass/fail
   status, and timestamp.
5. Exit with the test exit code so Jaypore CI records the run as passed or
   failed.
