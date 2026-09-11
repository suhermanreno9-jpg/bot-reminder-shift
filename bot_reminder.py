#!/usr/bin/env python3
"""
Bot Reminder 3 Shift Telegram
Fitur:
- Reminder otomatis sesuai shift aktif (Pagi/Siang/Malam)
- Tombol ✅ Done & ⏳ Pending di setiap reminder
- Jika Pending → reminder ulang 5 menit kemudian
- Jika Done → catat nama user yang konfirmasi
- Ganti shift via perintah bot
- Tambah/hapus/lihat jadwal via chat
"""

import logging
import json
import os
from datetime import datetime, time
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, JobQueue
)

# ─── KONFIGURASI ───────────────────────────────────────────────
TOKEN   = "8783710731:AAHpt21RKgJuCSppc3QSQ1jvXI_ZvMqrB8I"
CHAT_ID = "-4795285346"
TIMEZONE = ZoneInfo("Asia/Jakarta")
DATA_FILE = "shift_data.json"
# ───────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── JADWAL DEFAULT ────────────────────────────────────────────
DEFAULT_SCHEDULES = {
    "pagi": [
        ("07:00", "🌅 Req PGA"),
        ("07:45", "⏰ Reminder — 1 jam lagi"),
        ("08:00", "📊 Jadwal Bukti JP & Paito JP"),
        ("08:45", "⏰ Reminder — 1 jam lagi"),
        ("09:45", "⏰ Reminder — 1 jam lagi"),
        ("10:45", "⏰ Reminder — 1 jam lagi"),
        ("11:45", "⏰ Reminder — 1 jam lagi"),
        ("12:00", "🃏 Poker"),
        ("12:45", "⏰ Reminder — 1 jam lagi"),
        ("13:00", "⚽ BOLA"),
        ("13:10", "🎰 Macau"),
        ("13:40", "📈 Update TO"),
        ("13:45", "⏰ Reminder — 1 jam lagi"),
        ("13:55", "🎲 Sydney"),
        ("14:00", "🔄 Ganti Prediksi All & WD Report"),
        ("14:30", "⏰ Reminder — 1 jam lagi"),
    ],
    "siang": [
        ("15:00", "📊 Statistik, Data Selisih, dll"),
        ("15:45", "⏰ Reminder — 1 jam lagi"),
        ("16:00", "📝 Isi WLBC"),
        ("16:10", "🎰 Macau"),
        ("16:45", "⏰ Reminder — 1 jam lagi"),
        ("17:00", "🎟️ IDN Raffle"),
        ("17:45", "⏰ Reminder — 1 jam lagi / Update TO"),
        ("17:55", "🎲 Singapore"),
        ("18:05", "🌅 PGA, Update TO Kemarin & Slot Mingguan & Total Online"),
        ("18:45", "⏰ Reminder — 1 jam lagi"),
        ("19:00", "📈 Update TO"),
        ("19:10", "🎰 Macau"),
        ("19:45", "⏰ Reminder — 1 jam lagi"),
        ("20:45", "⏰ Reminder — 1 jam lagi"),
        ("21:00", "📋 WD Report"),
        ("21:45", "⏰ Reminder — 1 jam lagi"),
        ("22:10", "🎰 Macau"),
        ("22:35", "⏰ Reminder — 1 jam lagi"),
    ],
    "malam": [
        ("23:00", "📈 Update TO"),
        ("23:10", "🎰 Macau & HK"),
        ("23:45", "⏰ Reminder — 1 jam lagi"),
        ("00:00", "🎁 Pembagian Bonus"),
        ("00:10", "🎰 Macau"),
        ("00:20", "⚙️ Config, Pinjaman & Bersih-bersih"),
        ("00:45", "⏰ Reminder — 1 jam lagi"),
        ("01:45", "⏰ Reminder — 1 jam lagi"),
        ("02:45", "⏰ Reminder — 1 jam lagi"),
        ("03:30", "📈 Update TO Kemarin"),
        ("03:45", "⏰ Reminder — 1 jam lagi"),
        ("04:45", "⏰ Reminder — 1 jam lagi"),
        ("05:45", "⏰ Reminder — 1 jam lagi"),
        ("06:00", "📋 WD Report"),
        ("06:35", "⏰ Reminder — 1 jam lagi"),
    ]
}

SHIFT_EMOJI = {"pagi": "🌅", "siang": "🌆", "malam": "🌙"}
SHIFT_TIME  = {"pagi": "07:00–15:00", "siang": "15:00–23:00", "malam": "23:00–07:00"}

# ─── LOAD / SAVE DATA ──────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        if "schedules" not in data:
            data["schedules"] = DEFAULT_SCHEDULES
        if "active_shift" not in data:
            data["active_shift"] = "pagi"
        return data
    return {"active_shift": "pagi", "schedules": DEFAULT_SCHEDULES}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── BUAT TOMBOL DONE / PENDING ────────────────────────────────
def make_keyboard(waktu: str, pesan: str, shift: str) -> InlineKeyboardMarkup:
    # encode data ke callback_data (max 64 char)
    short = pesan[:30].replace("|", "-")
    cb_done    = f"done|{shift}|{waktu}|{short}"
    cb_pending = f"pending|{shift}|{waktu}|{short}"
    keyboard = [
        [
            InlineKeyboardButton("✅ Done",    callback_data=cb_done),
            InlineKeyboardButton("⏳ Pending", callback_data=cb_pending),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ─── KIRIM REMINDER ────────────────────────────────────────────
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job   = context.job
    shift = job.data["shift"]
    waktu = job.data["waktu"]
    pesan = job.data["pesan"]
    emoji = SHIFT_EMOJI.get(shift, "🔔")

    text = (
        f"{emoji} *REMINDER SHIFT {shift.upper()}*\n"
        f"🕐 {waktu} WIB\n"
        f"━━━━━━━━━━━━━━\n"
        f"{pesan}"
    )
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=text,
        parse_mode="Markdown",
        reply_markup=make_keyboard(waktu, pesan, shift)
    )

# ─── KIRIM REMINDER PENDING (5 menit kemudian) ─────────────────
async def send_pending_reminder(context: ContextTypes.DEFAULT_TYPE):
    job   = context.job
    shift = job.data["shift"]
    waktu = job.data["waktu"]
    pesan = job.data["pesan"]
    user  = job.data["user"]
    emoji = SHIFT_EMOJI.get(shift, "🔔")

    text = (
        f"{emoji} *REMINDER ULANG — SHIFT {shift.upper()}*\n"
        f"🕐 {waktu} WIB\n"
        f"━━━━━━━━━━━━━━\n"
        f"{pesan}\n\n"
        f"⚠️ Di-pending oleh: *{user}*"
    )
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=text,
        parse_mode="Markdown",
        reply_markup=make_keyboard(waktu, pesan, shift)
    )

# ─── HANDLER TOMBOL CALLBACK ───────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data_parts = query.data.split("|")
    action = data_parts[0]
    shift  = data_parts[1] if len(data_parts) > 1 else "?"
    waktu  = data_parts[2] if len(data_parts) > 2 else "?"
    pesan  = data_parts[3] if len(data_parts) > 3 else "?"

    # Nama user yang klik tombol
    user = query.from_user
    nama = user.first_name or ""
    if user.last_name:
        nama += f" {user.last_name}"
    if user.username:
        nama += f" (@{user.username})"

    now_str = datetime.now(TIMEZONE).strftime("%H:%M")

    if action == "done":
        new_text = (
            f"{query.message.text}\n\n"
            f"✅ *DONE* — dikerjakan oleh *{nama}*\n"
            f"🕐 Konfirmasi jam {now_str} WIB"
        )
        await query.edit_message_text(
            text=new_text,
            parse_mode="Markdown",
            reply_markup=None  # hapus tombol setelah done
        )

    elif action == "pending":
        new_text = (
            f"{query.message.text}\n\n"
            f"⏳ *PENDING* oleh *{nama}* — reminder ulang 5 menit lagi"
        )
        await query.edit_message_text(
            text=new_text,
            parse_mode="Markdown",
            reply_markup=None  # hapus tombol lama
        )
        # Jadwalkan reminder ulang 5 menit kemudian
        context.job_queue.run_once(
            send_pending_reminder,
            when=300,  # 5 menit = 300 detik
            name=f"pending_{waktu}_{now_str}",
            data={"shift": shift, "waktu": waktu, "pesan": pesan, "user": nama}
        )

# ─── DAFTARKAN SEMUA JOB ───────────────────────────────────────
def register_jobs(app: Application, data: dict):
    current_jobs = app.job_queue.jobs()
    for job in current_jobs:
        if job.name and job.name.startswith("reminder_"):
            job.schedule_removal()

    shift     = data["active_shift"]
    schedules = data["schedules"].get(shift, [])

    for waktu, pesan in schedules:
        try:
            h, m = map(int, waktu.split(":"))
            t = time(hour=h, minute=m, tzinfo=TIMEZONE)
            app.job_queue.run_daily(
                send_reminder,
                time=t,
                name=f"reminder_{shift}_{waktu.replace(':', '')}",
                data={"shift": shift, "waktu": waktu, "pesan": pesan}
            )
        except Exception as e:
            logger.error(f"Gagal daftarkan job {waktu}: {e}")

    logger.info(f"✅ {len(schedules)} reminder didaftarkan untuk shift {shift}")

# ─── COMMAND: /start ───────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data  = load_data()
    shift = data["active_shift"]
    emoji = SHIFT_EMOJI[shift]
    text = (
        "🤖 *Bot Reminder Shift* siap!\n\n"
        f"Shift aktif: {emoji} *{shift.upper()}* ({SHIFT_TIME[shift]})\n\n"
        "*Perintah:*\n"
        "• /shift — lihat & ganti shift\n"
        "• /jadwal — lihat semua jadwal\n"
        "• /tambah — tambah reminder\n"
        "• /hapus — hapus reminder\n"
        "• /bantuan — panduan lengkap"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── COMMAND: /shift ───────────────────────────────────────────
async def cmd_shift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    args = context.args

    if not args:
        shift = data["active_shift"]
        emoji = SHIFT_EMOJI[shift]
        text = (
            f"Shift aktif: {emoji} *{shift.upper()}* ({SHIFT_TIME[shift]})\n\n"
            "Untuk ganti:\n"
            "`/shift pagi` 🌅\n"
            "`/shift siang` 🌆\n"
            "`/shift malam` 🌙"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    new_shift = args[0].lower()
    if new_shift not in ["pagi", "siang", "malam"]:
        await update.message.reply_text("❌ Pilih: `pagi`, `siang`, atau `malam`", parse_mode="Markdown")
        return

    data["active_shift"] = new_shift
    save_data(data)
    register_jobs(context.application, data)

    emoji  = SHIFT_EMOJI[new_shift]
    jadwal = data["schedules"].get(new_shift, [])
    await update.message.reply_text(
        f"✅ Shift diganti ke {emoji} *{new_shift.upper()}*\n"
        f"⏰ {SHIFT_TIME[new_shift]}\n"
        f"📋 {len(jadwal)} reminder aktif",
        parse_mode="Markdown"
    )

# ─── COMMAND: /jadwal ──────────────────────────────────────────
async def cmd_jadwal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data  = load_data()
    args  = context.args
    shift = args[0].lower() if args and args[0].lower() in ["pagi","siang","malam"] else data["active_shift"]
    schedules = data["schedules"].get(shift, [])
    emoji = SHIFT_EMOJI[shift]

    if not schedules:
        await update.message.reply_text(f"Belum ada jadwal untuk shift {shift}.")
        return

    lines = [f"{emoji} *JADWAL SHIFT {shift.upper()}* ({SHIFT_TIME[shift]})\n"]
    for i, (waktu, pesan) in enumerate(schedules, 1):
        lines.append(f"`{i:02d}.` {waktu} — {pesan}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# ─── COMMAND: /tambah ──────────────────────────────────────────
async def cmd_tambah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    args = context.args

    if not args or len(args) < 2:
        await update.message.reply_text(
            "📝 *Format:*\n`/tambah [shift] HH:MM pesan`\n\n"
            "*Contoh:*\n`/tambah pagi 09:00 Update laporan`\n"
            "`/tambah 10:30 Cek data` (shift aktif)",
            parse_mode="Markdown"
        )
        return

    if args[0].lower() in ["pagi", "siang", "malam"]:
        shift = args[0].lower()
        rest  = args[1:]
    else:
        shift = data["active_shift"]
        rest  = args

    waktu = rest[0]
    pesan = " ".join(rest[1:]) if len(rest) > 1 else ""

    if not pesan:
        await update.message.reply_text("❌ Pesan tidak boleh kosong.")
        return

    try:
        h, m = map(int, waktu.split(":"))
        assert 0 <= h <= 23 and 0 <= m <= 59
    except:
        await update.message.reply_text("❌ Format waktu salah. Gunakan HH:MM", parse_mode="Markdown")
        return

    schedules = data["schedules"].get(shift, [])
    if waktu in [w for w, _ in schedules]:
        await update.message.reply_text(
            f"⚠️ Sudah ada reminder jam *{waktu}* di shift *{shift}*.\n"
            f"Hapus dulu: `/hapus {shift} {waktu}`",
            parse_mode="Markdown"
        )
        return

    schedules.append((waktu, pesan))
    schedules.sort(key=lambda x: x[0])
    data["schedules"][shift] = schedules
    save_data(data)

    if shift == data["active_shift"]:
        register_jobs(context.application, data)

    emoji = SHIFT_EMOJI[shift]
    await update.message.reply_text(
        f"✅ Reminder ditambahkan!\n{emoji} *{shift.upper()}* — {waktu} WIB\n📝 {pesan}",
        parse_mode="Markdown"
    )

# ─── COMMAND: /hapus ───────────────────────────────────────────
async def cmd_hapus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    args = context.args

    if not args:
        await update.message.reply_text(
            "🗑️ *Format:*\n`/hapus [shift] HH:MM`\n\n"
            "*Contoh:*\n`/hapus pagi 09:00`\n`/hapus 10:30`",
            parse_mode="Markdown"
        )
        return

    if args[0].lower() in ["pagi", "siang", "malam"]:
        shift = args[0].lower()
        waktu = args[1] if len(args) > 1 else None
    else:
        shift = data["active_shift"]
        waktu = args[0]

    if not waktu:
        await update.message.reply_text("❌ Masukkan waktu yang ingin dihapus.")
        return

    schedules    = data["schedules"].get(shift, [])
    original_len = len(schedules)
    schedules    = [(w, p) for w, p in schedules if w != waktu]

    if len(schedules) == original_len:
        await update.message.reply_text(
            f"❌ Tidak ada reminder jam *{waktu}* di shift *{shift}*.",
            parse_mode="Markdown"
        )
        return

    data["schedules"][shift] = schedules
    save_data(data)

    if shift == data["active_shift"]:
        register_jobs(context.application, data)

    await update.message.reply_text(
        f"✅ Reminder *{waktu} WIB* shift *{shift.upper()}* dihapus.",
        parse_mode="Markdown"
    )

# ─── COMMAND: /bantuan ─────────────────────────────────────────
async def cmd_bantuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 *Panduan Bot Reminder Shift*\n\n"
        "━━━━ TOMBOL REMINDER ━━━━\n"
        "✅ *Done* — tandai task selesai, catat nama kamu\n"
        "⏳ *Pending* — tunda 5 menit, reminder ulang otomatis\n\n"
        "━━━━ SHIFT ━━━━\n"
        "`/shift` — lihat shift aktif\n"
        "`/shift pagi` 🌅 | `/shift siang` 🌆 | `/shift malam` 🌙\n\n"
        "━━━━ JADWAL ━━━━\n"
        "`/jadwal` — shift aktif\n"
        "`/jadwal pagi` | `/jadwal siang` | `/jadwal malam`\n\n"
        "━━━━ KELOLA ━━━━\n"
        "`/tambah pagi 09:00 Nama task`\n"
        "`/hapus pagi 09:00`\n\n"
        "💡 Semua member group bisa pakai semua perintah."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── MAIN ──────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("shift",   cmd_shift))
    app.add_handler(CommandHandler("jadwal",  cmd_jadwal))
    app.add_handler(CommandHandler("tambah",  cmd_tambah))
    app.add_handler(CommandHandler("hapus",   cmd_hapus))
    app.add_handler(CommandHandler("bantuan", cmd_bantuan))
    app.add_handler(CallbackQueryHandler(button_handler))

    async def on_startup(app):
        data = load_data()
        register_jobs(app, data)
        await app.bot.set_my_commands([
            BotCommand("start",   "Menu utama"),
            BotCommand("shift",   "Lihat / ganti shift aktif"),
            BotCommand("jadwal",  "Lihat jadwal shift"),
            BotCommand("tambah",  "Tambah reminder baru"),
            BotCommand("hapus",   "Hapus reminder"),
            BotCommand("bantuan", "Panduan lengkap"),
        ])
        logger.info("✅ Bot started!")

    app.post_init = on_startup
    logger.info("🚀 Bot berjalan...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
