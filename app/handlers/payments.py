from telegram import Update, LabeledPrice
from telegram.ext import ContextTypes
from app.database import models
from app.utils.logger import setup_logger

logger = setup_logger("payments")

async def send_invoice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback triggered by the '⭐ Upgrade to PRO' inline button."""
    query = update.callback_query
    await query.answer()
    
    if query.data != "buy_pro":
        return
        
    chat_id = update.effective_chat.id
    title = "Easy English PRO"
    description = "Unlimited Voice Assistant replies and advanced conversational AI memory. Pay securely with Telegram Stars."
    payload = "pro_sub_payload"
    currency = "XTR"
    price = 10
    prices = [LabeledPrice("Easy English PRO", price)]
    
    try:
        await context.bot.send_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token="", # Empty is required for Telegram Stars XTR
            currency=currency,
            prices=prices
        )
    except Exception as e:
        logger.error(f"Failed to send XTR invoice: {e}")
        await context.bot.send_message(chat_id, "Error generating invoice. Please try again later.")

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Answers the PreCheckoutQuery allowing payment to proceed."""
    query = update.pre_checkout_query
    
    if query.invoice_payload != "pro_sub_payload":
        await query.answer(ok=False, error_message="Session expired or invalid payload.")
        return
        
    await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles logic after user successfully buys stars."""
    user_id = update.effective_user.id
    payment = update.message.successful_payment
    
    if payment.invoice_payload == "pro_sub_payload":
        await models.toggle_user_status(user_id, "is_pro", 1)
        await update.message.reply_text(
            "🎉 *Payment successful!*\n\nYou are now a PRO user. All trial restrictions have been permanently lifted.\n\nEnjoy unlimited Voice Replies and deep contextual memory!", 
            parse_mode="Markdown"
        )
