from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.database import models
from app.config.settings import config
from app.utils.logger import setup_logger

logger = setup_logger("admin_handlers")

def is_admin(user_id: int) -> bool:
    """Helper to check if user has admin privileges based on .env config."""
    return user_id in config.admin_ids_list

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows admin panel if user is admin."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return await update.message.reply_text("You do not have permission to use this command.")

    panel_text = (
        "🔐 *Admin Panel*\n\n"
        "Click a button below or use these commands directly:\n"
        "/stats - View bot statistics\n"
        "/broadcast [message] - Send a message to all users\n"
        "/ban [user_id] - Ban a user (revoke voice & ai)\n"
        "/unban [user_id] - Unban a user\n"
        "/toggle_ai [user_id] - Toggle AI for user\n"
        "/toggle_voice [user_id] - Toggle Voice for user\n"
        "/toggle_monetization - Toggle global monetization\n"
        "/grant_pro [user_id] - Grant Pro status"
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 View Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("💰 Toggle Monetization", callback_data="admin_monetization")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(panel_text, reply_markup=reply_markup, parse_mode="Markdown")

async def admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles admin panel button clicks."""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(update.effective_user.id):
        return
        
    if query.data == "admin_stats":
        users = await models.get_all_users()
        await query.message.reply_text(f"📊 *Statistics*\n\n👥 Total Users: {len(users)}", parse_mode="Markdown")
    elif query.data == "admin_monetization":
        current_setting = await models.get_global_setting("monetization", "false")
        new_val = "true" if current_setting == "false" else "false"
        await models.set_global_setting("monetization", new_val)
        config.MONETIZATION_ENABLED = (new_val == "true")
        status = "enabled" if new_val == "true" else "disabled"
        await query.message.reply_text(f"Global monetization feature {status}.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    users = await models.get_all_users()
    await update.message.reply_text(f"📊 *Statistics*\n\n👥 Total Users: {len(users)}", parse_mode="Markdown")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    
    if not context.args:
        return await update.message.reply_text("Usage: /broadcast <message>")
        
    message = " ".join(context.args)
    users = await models.get_all_users()
    
    sent = 0
    for uid in users:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 *Broadcast*\n\n{message}", parse_mode="Markdown")
            sent += 1
        except Exception as e:
            logger.warning(f"Failed to broadcast to {uid}: {e}")
            
    await update.message.reply_text(f"Broadcast sent to {sent}/{len(users)} users.")

async def toggle_status_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, db_field: str, success_msg: str):
    """Helper for banning/unbanning/toggling."""
    if not is_admin(update.effective_user.id): return
    if not context.args:
        return await update.message.reply_text(f"Usage: /{update.message.text.split()[0][1:]} <user_id>")
    
    try:
        target_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("Invalid user_id.")
        
    target_user = await models.get_user(target_id)
    if not target_user:
        return await update.message.reply_text("User not found in database.")

    current_val = target_user.get(db_field)
    new_val = 0 if current_val else 1
    
    if db_field in ['ai_enabled', 'voice_enabled']:
        await models.update_user_feature(target_id, db_field, new_val)
    elif db_field in ['is_pro', 'is_admin']:
        await models.toggle_user_status(target_id, db_field, new_val)
    # Mapping ban to ai_enabled=0 AND voice_enabled=0
    elif db_field == 'ban':
        await models.update_user_feature(target_id, 'ai_enabled', 0)
        await models.update_user_feature(target_id, 'voice_enabled', 0)
        new_val = 1 # Just for formatting
    elif db_field == 'unban':
        await models.update_user_feature(target_id, 'ai_enabled', 1)
        await models.update_user_feature(target_id, 'voice_enabled', 1)
        new_val = 0 # Just for formatting
        
    status = "enabled" if new_val else "disabled"
    if db_field == 'ban': status = "banned"
    if db_field == 'unban': status = "unbanned"
    await update.message.reply_text(f"User {target_id} {success_msg} ({status}).")

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await toggle_status_wrapper(update, context, 'ban', "access restricted")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await toggle_status_wrapper(update, context, 'unban', "access restored")

async def toggle_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await toggle_status_wrapper(update, context, 'ai_enabled', "AI communication toggled")
    
async def toggle_voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await toggle_status_wrapper(update, context, 'voice_enabled', "Voice communication toggled")

async def grant_pro_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await toggle_status_wrapper(update, context, 'is_pro', "Pro status toggled")

async def toggle_monetization_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    
    # Check current DB settings
    current_setting = await models.get_global_setting("monetization", "false")
    new_val = "true" if current_setting == "false" else "false"
    await models.set_global_setting("monetization", new_val)
    
    # We update in-memory running config if necessary, but DB takes precedence if queried
    config.MONETIZATION_ENABLED = (new_val == "true")
    
    status = "enabled" if new_val == "true" else "disabled"
    await update.message.reply_text(f"Global monetization feature {status}.")
