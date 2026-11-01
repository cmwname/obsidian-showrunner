---
type: project
project: Upload bot
status: paused
updated: 2026-10-21
next: pick a server
---

> [!summary]- Summary
> Telegram bot that posts new videos to the channel chat. Works locally on long polling; waits for a server.

# Upload bot

Telegram bot that posts new videos to the channel's chat. Code in `bot/`.

## Now

- Works locally on long polling. Token in `.env` as `BOT_TOKEN`.

## Decisions

- 21.10: long polling for now, webhooks once there is a server.
