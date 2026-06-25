import os
import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

# فعال‌سازی Logger برای عیب‌یابی
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- اطلاعات اختصاصی شما ---
BOT_TOKEN = "8894155985:AAFwVhLpEy5QuxlJzA9G65wx28mZb4aeGKA"
GROUP_CHAT_ID = "-3963196618"
RENDER_APP_URL = "https://cleaning-tel-bot-new.onrender.com" 

# مراحل گفتگو (States)
CHOOSING_PERSON, CHOOSING_ZONE, CHOOSING_TASKS = range(3)

# داده‌های ثابت
PEOPLE = ["پیمان", "فاطمه", "روشنک", "نیلوفر"]
ZONES = {"1": "نظافت مناطق مشترک", "2": "نظافت مستراح"}

TASKS = {
    "نظافت مناطق مشترک": [
        "کف سرامیک", "سینک روشویی", "کابینت ها", 
        "گاز", "اوپن", "بالکن", "تمیز کردن خشک کن"
    ],
    "نظافت مستراح": [
        "حمام", "کف سرویس", "آینه", "شست و شو و ضد عفونی بیده",
        "شست و شو و ضد عفونی توالت", "کمد", "سینک روشویی",
        "تعویض پلاستیک زباله", "شست و شو و ضد عفونی فرچه توالت", "نظافت طی"
    ]
}

async def group_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ["group", "supergroup"]:
        bot_username = (await context.bot.get_me()).username
        start_link = f"https://t.me/{bot_username}?start=group"
        
        keyboard = [[InlineKeyboardButton("🧹 شروع ثبت گزارش نظافت", url=start_link)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "📋 **سامانه ثبت گزارش نظافت منزل**\n\n"
            "دوستان عزیز، هر زمان که نوبت نظافت شما بود، برای ثبت کارهای انجام شده لطفاً روی دکمه زیر کلیک کنید.\n"
            "مراحل ثبت در پی‌وی ربات انجام شده و گزارش نهایی خودکار به همین گروه ارسال می‌شود."
        )
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        try:
            await update.message.delete()
        except Exception:
            pass
    else:
        await update.message.reply_text("❌ این دستور فقط مخصوص اجرا در گروه است.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear() 
    
    keyboard = [[InlineKeyboardButton(person, callback_data=f"p_{person}")] for person in PEOPLE]
    keyboard.append([InlineKeyboardButton("❌ لغو عملیات", callback_data="cancel_conv")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "🧹 **برنامه نظافت خونه**\nلطفا فرد مسئول را انتخاب کنید:"
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        
    return CHOOSING_PERSON

async def person_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    person = query.data.split("_")[1]
    context.user_data["person"] = person
    
    keyboard = [
        [InlineKeyboardButton(ZONES["1"], callback_data="z_1")],
        [InlineKeyboardButton(ZONES["2"], callback_data="z_2")],
        [InlineKeyboardButton("🔙 بازگشت به مرحله قبل", callback_data="back_to_person"),
         InlineKeyboardButton("❌ لغو", callback_data="cancel_conv")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"👤 مسئول: **{person}**\n\n📍 لطفا منطقه نظافت را انتخاب کنید:", 
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return CHOOSING_ZONE

async def show_zones_again(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton(ZONES["1"], callback_data="z_1")],
        [InlineKeyboardButton(ZONES["2"], callback_data="z_2")],
        [InlineKeyboardButton("🔙 بازگشت به مرحله قبل", callback_data="back_to_person"),
         InlineKeyboardButton("❌ لغو", callback_data="cancel_conv")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=f"👤 مسئول: **{context.user_data.get('person', 'نامشخص')}**\n\n📍 لطفا منطقه نظافت را انتخاب کنید:", 
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return CHOOSING_ZONE

async def zone_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    zone_code = query.data.split("_")[1]
    zone_name = ZONES.get(zone_code, "نامشخص")
    context.user_data["zone"] = zone_name
    
    if "selected_tasks" not in context.user_data:
        context.user_data["selected_tasks"] = []
    
    await show_tasks_keyboard(query, context)
    return CHOOSING_TASKS

async def show_tasks_keyboard(query, context):
    zone_name = context.user_data.get("zone", "نامشخص")
    selected_tasks = context.user_data.get("selected_tasks", [])
    all_tasks = TASKS.get(zone_name, [])
    
    keyboard = []
    for task in all_tasks:
        status = "✅ " if task in selected_tasks else "⬜ "
        keyboard.append([InlineKeyboardButton(f"{status}{task}", callback_data=f"t_{task}")])
    
    keyboard.append([
        InlineKeyboardButton("🔵 ثبت نهایی", callback_data="submit_report"),
        InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_zone")
    ])
    keyboard.append([
        InlineKeyboardButton("❌ لغو", callback_data="cancel_conv")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"👤 مسئول: **{context.user_data.get('person')}**\n📍 منطقه: **{zone_name}**\n\n📋 کارهای انجام شده را تیک بزنید:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def task_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    try:
        task_name = query.data.split("t_")[1]
    except IndexError:
        return CHOOSING_TASKS

    selected_tasks = context.user_data.get("selected_tasks", [])
    
    if task_name in selected_tasks:
        selected_tasks.remove(task_name)
    else:
        selected_tasks.append(task_name)
        
    context.user_data["selected_tasks"] = selected_tasks
    await show_tasks_keyboard(query, context)
    return CHOOSING_TASKS

async def submit_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    person = context.user_data.get("person", "نامشخص")
    zone = context.user_data.get("zone", "نامشخص")
    selected_tasks = context.user_data.get("selected_tasks", [])
    
    if not selected_tasks:
        selected_tasks_str = "• هیچ کاری انتخاب نشده است."
    else:
        selected_tasks_str = "\n".join([f"• {t}" for t in selected_tasks])
        
    now_gregorian = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    report_text = (
        f"✨ **گزارش نظافت جدید** ✨\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 **پیک می:** {person}\n"
        f"📍 **منطقه:** {zone}\n"
        f"📅 **تاریخ و زمان:** {now_gregorian}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📋 **کارهای انجام شده:**\n{selected_tasks_str}"
    )
    
    try:
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=report_text, parse_mode="Markdown")
        await query.edit_message_text("✅ گزارش با موفقیت ثبت و به گروه ارسال شد.")
    except Exception as e:
        await query.edit_message_text(f"❌ خطا در ارسال به گروه. مطمئن شوید بات در گروه عضو است.\nخطا: {e}")
        
    return ConversationHandler.END

async def timeout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = "⏱ زمان پاسخگویی شما به پایان رسید. برای شروع مجدد دستور /start را ارسال کنید."
    if update.callback_query:
        await update.callback_query.edit_message_text(msg)
    elif update.message:
        await update.message.reply_text(msg)
    return ConversationHandler.END

async def cancel_inline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ عملیات ثبت گزارش نظافت لغو شد.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ عملیات ثبت گزارش نظافت لغو شد.")
    return ConversationHandler.END

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("group_setup", group_setup))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_PERSON: [
                CallbackQueryHandler(cancel_inline, pattern="^cancel_conv$"),
                CallbackQueryHandler(person_chosen, pattern="^p_")
            ],
            CHOOSING_ZONE: [
                CallbackQueryHandler(cancel_inline, pattern="^cancel_conv$"),
                CallbackQueryHandler(start, pattern="^back_to_person$"),
                CallbackQueryHandler(zone_chosen, pattern="^z_")
            ],
            CHOOSING_TASKS: [
                CallbackQueryHandler(cancel_inline, pattern="^cancel_conv$"),
                CallbackQueryHandler(show_zones_again, pattern="^back_to_zone$"),
                CallbackQueryHandler(submit_report, pattern="^submit_report$"),
                CallbackQueryHandler(task_toggle, pattern="^t_")
            ],
            ConversationHandler.TIMEOUT: [
                CallbackQueryHandler(timeout_handler), 
                CommandHandler("start", start)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=180 
    )

    application.add_handler(conv_handler)
    
    port = int(os.environ.get("PORT", 10000))
    
    # اجرای وب‌هوک روی سرور رندر
    if RENDER_APP_URL and "onrender.com" in RENDER_APP_URL:
        logger.info("Starting Webhook on Render...")
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=RENDER_APP_URL
        )
    else:
        logger.info("Starting Polling (Local Mode)...")
        application.run_polling(close_loop=False, drop_pending_updates=True)

if __name__ == "__main__":
    main()
