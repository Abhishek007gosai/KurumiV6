# Combined FileStore + LinkShare Bot

This is **FileStore** and **LinkBot** merged into a single
Pyrogram bot. It runs as one process with one `/start` command, one
database connection, and no duplicate handlers.

## How the merge was done

KafkaLinkBotV1 was used as the base (bigger, more complete DB layer and
a full `/settings` UI). KurumiFileStoreV2's unique features were ported
on top of it:

| Feature | Source | Notes |
|---|---|---|
| Channel invite/request links, `/settings` UI, ban menu, fsub menu | Kafka | unchanged |
| Auto-approve join requests | Kafka | unchanged |
| `/broadcast` (reply-to-message) | Kafka | unchanged, already existed in `start.py` |
| File storage — forward a file, get a link | Kurumi | **renamed**, see below |
| `/pbroadcast`, `/dbroadcast` | Kurumi | added — Kafka didn't have these |
| `/ban`, `/unban`, `/banlist` slash commands | Kurumi | added, shares the *same* `ban_data` collection as Kafka's ban menu, so both stay in sync |
| `/add_admin`, `/deladmin`, `/admins` | Kurumi | added |
| `/stats`, `/users`, `/dlt_time`, `/check_dlt_time` | Kurumi | added |

### Why some commands were renamed

Both bots independently used `/genlink` and `/batch` for two **different**
features:
- Kafka: generate an invite/request link for an already-existing channel.
- Kurumi: forward a post to the bot and get a link that re-sends it (file store).

Keeping both under the same command name would silently break one of them.
The file-store versions were renamed:

- `/genlink` → **`/filelink`**
- `/batch` → **`/fbatch`**
- `custom_batch` → **`/customfbatch`**

Kafka's `/genlink` and `/batch` (channel links) keep their original names.

### Other conflicts fixed while merging

- Kafka's `plugins/settings.py` calls `client.listen(...)` in its ban
  menu, but the project never imported `pyromod.listen` anywhere — this
  would have crashed with `AttributeError` the first time an admin tried
  to ban someone via `/settings`. Fixed in `bot.py`.
- Kurumi's `banuser.py` used its own ban collection with different field
  names than Kafka's ban menu. Both now read/write the same schema via
  new `database.py` methods (`ban_user_exist`, `add_ban_user`,
  `del_ban_user`, `get_ban_users`), so banning someone from `/ban` or
  from `/settings` has the same effect.
- Removed hardcoded `API_HASH`/`OWNER_ID`/`APP_ID` default values that
  were sitting in Kafka's original `config.py` — always set these via
  environment variables, never commit real credentials.

## New file-store flow

`/start`-links look like `https://t.me/YourBot?start=<payload>`. The bot
decodes the payload and checks whether it's a channel-link payload
(plain integer, Kafka's feature) or a file-store payload (`get-...`,
Kurumi's feature) and routes accordingly. This logic lives in
`plugins/start.py` (`deliver_stored_files`).

## Environment variables

Required:
- `TG_BOT_TOKEN`, `APP_ID`, `API_HASH` — from @BotFather / my.telegram.org
- `OWNER_ID` — your numeric Telegram user ID
- `DATABASE_URL` (or `DB_URI`) — MongoDB connection string
- `DATABASE_NAME` (or `DB_NAME`) — Mongo database name

Optional:
- `CHANNEL_ID` — a private channel the bot is admin in, used to archive
  files for `/filelink`, `/fbatch`, `/customfbatch`. Leave unset to
  disable file-store commands and run link-sharing only.
- `DATABASE_CHANNEL` — channel/chat for restart notifications
- `PORT` (default `8080`), `TG_BOT_WORKERS` (default `100`)
- `FSUB_LINK_EXPIRY`, `START_PIC`, `FORCE_PIC`, `FSUB_PIC`,
  `CUSTOM_CAPTION`, `PROTECT_CONTENT`, `BAN_SUPPORT`, `OWNER`,
  `BOT_USERNAME`, `START_MESSAGE`, `HELP_MESSAGE`, `ABOUT_MESSAGE`,
  `FORCE_SUB_MESSAGE`

## Running

```bash
pip install -r requirements.txt
python3 main.py
```

## Command list

See `/commands` inside the bot (admin-only) for the full list — it's
also defined in `CMD_TXT` in `config.py`.

# What changed (base: KurumiV3, which was already a Link-Share + File-Store merge)

## 1. Shortener verification (ported from ForYou, fully bot-manageable)
- New: `plugins/shortener.py`, `helper_func.shorten_url()`, new DB collections.
- Everything is set from inside the bot — **no .env editing needed**:
  - `/shortener` or `/settings → 🔗 Shortener` opens the menu
  - Set API key, website, video tutorial link, verify message text
  - Toggle forward/copy **protection** on the verification message
  - Set **validity in days** (owner-only). `0` = user must verify again on
    every single post/link. Any other number = they get N days free access
    after one verification.
- Gate is applied to file delivery (`/genlink`, `/batch`, `/custom_batch`
  links). Admins always bypass it.
- Premium/pro users (see below) always bypass it too.

## 2. Premium/Pro users (ported from KurumiFileStoreV2 — Yato branch)
- New: `plugins/premium.py`
- `/addpremium <id> [1 day|2 weeks|1 month|1 year]` (owner only) — grants a
  shortener-free pass, temporary or permanent
- `/delpremium <id>`, `/premiumusers`

## 3. Bot Mode: Link Share ⇄ File Store
- New: `plugins/bot_mode.py`, `/mode` command, `/settings → ⚙️ Bot Mode`
- `/genlink`, `/batch`, `/custom_batch` (the file-store commands — renamed
  from `/filelink` `/fbatch` `/customfbatch`) now **only work in File Store
  mode**.
- The old `/genlink` and `/batch` commands from the Link-Share side
  (channel invite links) were **removed as slash commands** — that feature
  still exists, just through the buttons in `/settings → Link Share Menu`,
  so the names aren't wasted.

## 4. Caption control from the bot
- New: `plugins/caption_settings.py`, `/caption` command
- OFF (default): delivered files keep their own original caption.
- ON: uses your custom caption text (`{filename}`, `{previouscaption}`
  placeholders), editable any time from the bot.

## 5. New admin commands
- `/listchnl` — list force-sub channels
- `/fsub_mode` — open the force-sub add/remove/toggle menu
  (both just jump into the existing Fsub Menu in `/settings` — no logic
  duplicated)
- `/add_admin`, `/deladmin`, `/admins` — already existed in KurumiV3, kept as-is

## 6. Auto-approve
- Checked `plugins/approve.py` — it already sends a **text-only** approval
  message with no photo and no buttons, so nothing needed changing there.

## Setup notes
- All the new settings live in MongoDB (`bot_settings`, `shortener_verify`
  collections) — nothing to configure in `config.py` for these features.
- You still need the existing env vars: `TG_BOT_TOKEN`, `APP_ID`,
  `API_HASH`, `OWNER_ID`, `CHANNEL_ID` (DB channel for file store),
  `DATABASE_URL`, `DATABASE_NAME`.
- First run: use `/mode` to pick Link Share or File Store, then
  `/shortener` to turn the shortener on and fill in your API key + site.
