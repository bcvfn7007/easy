from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.database import models
from app.config.settings import config
from app.utils.logger import setup_logger
from app.database.db import get_db

logger = setup_logger("admin_handlers")

def is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids_list

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("👥 Manage Users", callback_data="admin_users_0")],
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("⚙️ System Settings", callback_data="admin_sys")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return await update.message.reply_text("You do not have permission to use this command.")

    panel_text = (
        "🔐 *Admin Control Panel*\n\n"
        "Welcome to the master control zone. Choose an action below:"
    )
    await update.message.reply_text(panel_text, reply_markup=get_admin_main_keyboard(), parse_mode="Markdown")

async def get_users_page(page: int, limit: int = 5) -> list:
    async with get_db() as db:
        offset = page * limit
        async with db.execute("SELECT user_id, first_name FROM users ORDER BY joined_at DESC LIMIT ? OFFSET ?", (limit, offset)) as cursor:
            rows = await cursor.fetchall()
            return rows if rows else []
            
async def get_total_users() -> int:
    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not is_admin(update.effective_user.id):
        return
        
    data = query.data
    
    if data == "admin_main":
        await query.edit_message_text("🔐 *Admin Control Panel*\n\nPlease select an option:", reply_markup=get_admin_main_keyboard(), parse_mode="Markdown")
        
    elif data == "admin_stats":
        total = await get_total_users()
        text = (
            f"📊 *Bot Statistics*\n\n"
            f"👥 Total Registered Users: {total}\n"
            f"_More detailed analytics coming soon._"
        )
        kb = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="admin_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        
    elif data == "admin_sys":
        current_setting = await models.get_global_setting("monetization", "false")
        status = "🟢 Enabled" if current_setting == "true" else "🔴 Disabled"
        text = "⚙️ *System Settings*\n\nManage global system parameters."
        kb = [
            [InlineKeyboardButton(f"Monetization: {status}", callback_data="admin_t_sys_mon")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        
    elif data == "admin_t_sys_mon":
        current = await models.get_global_setting("monetization", "false")
        new_val = "true" if current == "false" else "false"
        await models.set_global_setting("monetization", new_val)
        config.MONETIZATION_ENABLED = (new_val == "true")
        
        status = "🟢 Enabled" if new_val == "true" else "🔴 Disabled"
        kb = [
            [InlineKeyboardButton(f"Monetization: {status}", callback_data="admin_t_sys_mon")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_main")]
        ]
        try:
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
        except Exception:
            pass
        
    elif data.startswith("admin_users_"):
        page = int(data.split("_")[2])
        users = await get_users_page(page)
        total = await get_total_users()
        
        kb = []
        for u in users:
            kb.append([InlineKeyboardButton(f"👤 {u[1]} ({u[0]})", callback_data=f"admin_user_{u[0]}")])
            
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin_users_{page-1}"))
        if (page + 1) * 5 < total:
            nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin_users_{page+1}"))
            
        if nav:
            kb.append(nav)
            
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="admin_main")])
        
        text = f"👥 *Manage Users* (Page {page+1})\nSelect a user to manage:"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        
    elif data.startswith("admin_user_"):
        uid = int(data.split("_")[2])
        u = await models.get_user(uid)
        if not u:
            return await query.edit_message_text("User not found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_users_0")]]))
            
        status_ai = "🟢" if u.get("ai_enabled") else "🔴"
        status_voice = "🟢" if u.get("voice_enabled") else "🔴"
        status_pro = "⭐ PRO" if u.get("is_pro") else "Trial/Free"
        
        text = (
            f"👤 *User Management*\n\n"
            f"📛 Name: {u.get('first_name')}\n"
            f"🆔 ID: `{uid}`\n"
            f"👑 Status: {status_pro}\n"
            f"🤖 AI Access: {status_ai}\n"
            f"🎤 Voice Access: {status_voice}"
        )
        
        kb = [
            [
                InlineKeyboardButton(f"Toggle AI {status_ai}", callback_data=f"admin_t_ai_{uid}"),
                InlineKeyboardButton(f"Toggle Voice {status_voice}", callback_data=f"admin_t_voice_{uid}")
            ],
            [
                InlineKeyboardButton("Toggle PRO", callback_data=f"admin_t_pro_{uid}"),
                InlineKeyboardButton("🛑 BAN", callback_data=f"admin_t_ban_{uid}") if (u.get("ai_enabled") or u.get("voice_enabled")) else InlineKeyboardButton("✅ UNBAN", callback_data=f"admin_t_unban_{uid}")
            ],
            [InlineKeyboardButton("🔙 Back to Users", callback_data="admin_users_0")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        
    elif data.startswith("admin_t_"):
        parts = data.split("_")
        action = parts[2]
        
        if action == "sys":
            return
            
        uid = int(parts[3])
        
        u = await models.get_user(uid)
        if not u: return
        
        if action == "ai":
            await models.update_user_feature(uid, "ai_enabled", 0 if u.get("ai_enabled") else 1)
        elif action == "voice":
            await models.update_user_feature(uid, "voice_enabled", 0 if u.get("voice_enabled") else 1)
        elif action == "pro":
            await models.toggle_user_status(uid, "is_pro", 0 if u.get("is_pro") else 1)
        elif action == "ban":
            await models.update_user_feature(uid, "ai_enabled", 0)
            await models.update_user_feature(uid, "voice_enabled", 0)
        elif action == "unban":
            await models.update_user_feature(uid, "ai_enabled", 1)
            await models.update_user_feature(uid, "voice_enabled", 1)
            
        query.data = f"admin_user_{uid}"
        await admin_callbacks(update, context)

async def _obsolete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fallback for old text commands."""
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("This command is obsolete. Please use the interactive /admin panel.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE): await _obsolete_command(update, context)
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE): await _obsolete_command(update, context)
async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE): await _obsolete_command(update, context)
async def toggle_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE): await _obsolete_command(update, context)
async def toggle_voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE): await _obsolete_command(update, context)
async def grant_pro_command(update: Update, context: ContextTypes.DEFAULT_TYPE): await _obsolete_command(update, context)
async def toggle_monetization_command(update: Update, context: ContextTypes.DEFAULT_TYPE): await _obsolete_command(update, context)

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args:
        return await update.message.reply_text("Usage: /broadcast <message>\n\nThis will send the message to all registered users.")
    msg = " ".join(context.args)
    users = await models.get_all_users()
    sent = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, f"📢 *Admin Broadcast*\n\n{msg}", parse_mode="Markdown")
            sent += 1
        except Exception as e:
            logger.warning(f"Broadcast failed for {uid}: {e}")
            pass
    await update.message.reply_text(f"Broadcast sent successfully to {sent}/{len(users)} users.")
