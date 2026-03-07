# Example 07 — Secrets with SOPS + Telegram

This Jaypore CI example shows how to keep secrets (API tokens, credentials)
encrypted inside your repository using [Mozilla SOPS](https://github.com/getsops/sops)
and decrypt them at CI time. The decrypted values are used to send a Telegram
notification with the build result.

## How it works

| Step | What happens |
|------|-------------|
| 1 | If `sops` is installed and `secrets.enc.json` exists, decrypt it to obtain `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. |
| 2 | If SOPS is unavailable, fall back to plain environment variables. |
| 3 | Run `python3 manage.py test core` and capture the result. |
| 4 | Send a Markdown-formatted message to Telegram with the build status. |
| 5 | Save all artifacts to `$JCI_OUTPUT_DIR`. |

## Artifacts produced

| File | Description |
|------|-------------|
| `test_output.txt` | Full test output. |
| `exit_code.txt` | Exit code from the test run. |
| `telegram_response.json` | Telegram API response (when notification is sent). |

## Setting up SOPS

### 1. Install SOPS

```bash
# Debian / Ubuntu
curl -LO https://github.com/getsops/sops/releases/download/v3.9.4/sops_3.9.4_amd64.deb
sudo dpkg -i sops_3.9.4_amd64.deb

# macOS
brew install sops
```

### 2. Choose an encryption backend

SOPS supports **age**, **GPG**, **AWS KMS**, **GCP KMS**, and **Azure Key Vault**.
For local / small-team use, [age](https://github.com/FiloSottile/age) is the
simplest option:

```bash
# Install age
sudo apt install age        # Debian/Ubuntu
brew install age            # macOS

# Generate a key pair
age-keygen -o ~/.config/sops/age/keys.txt
# Note the public key printed to stdout (starts with "age1...")
```

### 3. Create a `.sops.yaml` config (optional but recommended)

Place this in your repository root so SOPS knows which key to use:

```yaml
creation_rules:
  - path_regex: secrets\.enc\.json$
    age: "age1your-public-key-here"
```

### 4. Create and encrypt the secrets file

Start from the provided template:

```bash
cp secrets.example.json secrets.json
```

Edit `secrets.json` with your real values:

```json
{
    "TELEGRAM_BOT_TOKEN": "123456789:ABCdefGHI-JKLmnoPQRstUVwxyz",
    "TELEGRAM_CHAT_ID": "-1001234567890"
}
```

Encrypt it:

```bash
sops -e secrets.json > secrets.enc.json
```

Now commit `secrets.enc.json` (the encrypted version) and **delete the
plaintext** `secrets.json`:

```bash
rm secrets.json
git add secrets.enc.json
git commit -m "Add encrypted secrets"
```

> **Never commit the plaintext `secrets.json`.**  Add it to `.gitignore`.

### 5. Decrypt (what run.sh does)

At CI time the script runs:

```bash
sops -d secrets.enc.json
```

This prints the decrypted JSON to stdout. The script parses it with Python to
extract individual values into environment variables.

Decryption requires the private key. For `age`, the key file at
`~/.config/sops/age/keys.txt` is used automatically.

## Alternative: plain environment variables

If you prefer not to use SOPS, export the variables before running CI:

```bash
export TELEGRAM_BOT_TOKEN="123456789:ABCdefGHI-JKLmnoPQRstUVwxyz"
export TELEGRAM_CHAT_ID="-1001234567890"
git jci run
```

The script detects that SOPS is absent (or that the encrypted file is missing)
and falls back to whatever `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are
already set in the environment.

## Setting up Telegram

1. Create a bot via [BotFather](https://t.me/BotFather) and note the **bot
   token**.
2. Get your **chat ID** by sending a message to the bot and visiting
   `https://api.telegram.org/bot<TOKEN>/getUpdates`.
3. Put both values into `secrets.json` and encrypt with SOPS (see above), or
   export them as environment variables.

## Project layout

```
your-repo/
├── manage.py
├── mysite/
│   └── settings.py
├── core/                    # the Django app under test
├── secrets.enc.json         # encrypted secrets (committed)
├── secrets.example.json     # template with placeholder values
├── .sops.yaml               # SOPS config (optional)
└── .jci/
    └── run.sh               # ← this script
```

## How to use

1. Copy the `.jci/` directory and `secrets.example.json` into your repo:

   ```bash
   cp -r 07-secrets-telegram/.jci /path/to/your-repo/.jci
   cp 07-secrets-telegram/secrets.example.json /path/to/your-repo/
   ```

2. Set up SOPS and encrypt your secrets (see above), or export them as
   environment variables.

3. Run Jaypore CI:

   ```bash
   git jci run
   ```
