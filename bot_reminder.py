#!/usr/bin/env python3
"""
Bot Reminder 3 Shift Telegram
Fitur:
- Reminder otomatis sesuai shift aktif (Pagi/Siang/Malam)
- Ganti shift via perintah bot
- Tambah/hapus/lihat jadwal via chat
- Semua member group bisa ganti shift & kelola jadwal
"""

import logging
import json
import os
from datetime import datetime, time
from zoneinfo import ZoneInfo

from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, ContextTypes, JobQueue
)

# ─── KONFIGURASI ───────────────────────────────────────────────
TOKEN = "8783710731:AAEPvqnYy7Za_MIftAAbIWgobp5kc8-R03M"   # Ganti dengan token dari @BotFather
CHAT_ID = "-4795285346"      # Ganti dengan chat_id group/channel tujuan
TIMEZONE = ZoneInfo("Asia/Jakarta")
DATA_FILE = "shift_data.json"           # File penyimpanan data
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
        ("09:45", "⏰ Reminder — 1 jam lagi @pakustadddke2"),
        ("10:45", "⏰ Reminder — 1 jam lagi @pakustadddke2"),
        ("11:45", "⏰ Reminder — 1 jam lagi @pakustadddke2"),
        ("12:00", "🃏 Poker"),
        ("12:45", "⏰ Reminder — 1 jam lagi @pakustadddke2"),
        ("13:00", "⚽ BOLA"),
        ("13:10", "🎰 Macau"),
        ("13:40", "📈 Update TO"),
        ("13:45", "⏰ Reminder — 1 jam lagi @pakustadddke2"),
        ("13:55", "🎲 Sydney"),
        ("14:00", "🔄 Ganti Prediksi All & WD Report"),
        ("14:30", "⏰ Reminder — 1 jam lagi @pakustadddke2"),
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
        ("19:45", "⏰ Reminder — 1 jam lagi "),
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
        # Pastikan semua key ada
        if "schedules" not in data:
            data["schedules"] = DEFAULT_SCHEDULES
        if "active_shift" not in data:
            data["active_shift"] = "pagi"
        return data
    return {"active_shift": "pagi", "schedules": DEFAULT_SCHEDULES}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── KIRIM REMINDER ────────────────────────────────────────────
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    shift  = job.data["shift"]
    waktu  = job.data["waktu"]
    pesan  = job.data["pesan"]
    emoji  = SHIFT_EMOJI.get(shift, "🔔")

    text = (
        f"{emoji} *REMINDER SHIFT {shift.upper()}*\n"
        f"🕐 {waktu} WIB\n"
        f"━━━━━━━━━━━━━━\n"
        f"{pesan}"
    )
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=text,
        parse_mode="Markdown"
    )

# ─── DAFTARKAN SEMUA JOB ───────────────────────────────────────
def register_jobs(app: Application, data: dict):
    # Hapus semua job reminder lama
    current_jobs = app.job_queue.jobs()
    for job in current_jobs:
        if job.name and job.name.startswith("reminder_"):
            job.schedule_removal()

    shift = data["active_shift"]
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
    data = load_data()
    shift = data["active_shift"]
    emoji = SHIFT_EMOJI[shift]
    text = (
        "🤖 *Bot Reminder Shift* siap!\n\n"
        f"Shift aktif sekarang: {emoji} *{shift.upper()}* ({SHIFT_TIME[shift]})\n\n"
        "*Perintah yang tersedia:*\n"
        "• /shift — lihat & ganti shift aktif\n"
        "• /jadwal — lihat semua jadwal shift ini\n"
        "• /tambah — tambah reminder baru\n"
        "• /hapus — hapus reminder\n"
        "• /bantuan — panduan lengkap"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── COMMAND: /shift ───────────────────────────────────────────
async def cmd_shift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    args = context.args

    if not args:
        # Tampilkan shift aktif
        shift = data["active_shift"]
        emoji = SHIFT_EMOJI[shift]
        text = (
            f"Shift aktif: {emoji} *{shift.upper()}* ({SHIFT_TIME[shift]})\n\n"
            "Untuk ganti shift:\n"
            "`/shift pagi` — 🌅 07:00–15:00\n"
            "`/shift siang` — 🌆 15:00–23:00\n"
            "`/shift malam` — 🌙 23:00–07:00"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    new_shift = args[0].lower()
    if new_shift not in ["pagi", "siang", "malam"]:
        await update.message.reply_text(
            "❌ Shift tidak valid. Pilih: `pagi`, `siang`, atau `malam`",
            parse_mode="Markdown"
        )
        return

    data["active_shift"] = new_shift
    save_data(data)
    register_jobs(context.application, data)

    emoji = SHIFT_EMOJI[new_shift]
    jadwal = data["schedules"].get(new_shift, [])
    await update.message.reply_text(
        f"✅ Shift diganti ke {emoji} *{new_shift.upper()}*\n"
        f"⏰ {SHIFT_TIME[new_shift]}\n"
        f"📋 {len(jadwal)} reminder aktif",
        parse_mode="Markdown"
    )

# ─── COMMAND: /jadwal ──────────────────────────────────────────
async def cmd_jadwal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    args = context.args
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
    """
    Format: /tambah [shift] HH:MM pesan
    Contoh: /tambah pagi 09:00 Update laporan harian
            /tambah 10:30 Cek data (pakai shift aktif)
    """
    data = load_data()
    args = context.args

    if not args or len(args) < 2:
        await update.message.reply_text(
            "📝 *Format:*\n"
            "`/tambah [shift] HH:MM pesan`\n\n"
            "*Contoh:*\n"
            "`/tambah pagi 09:00 Update laporan`\n"
            "`/tambah 10:30 Cek data` (pakai shift aktif)\n\n"
            "Shift: `pagi`, `siang`, `malam`",
            parse_mode="Markdown"
        )
        return

    # Deteksi apakah arg pertama adalah nama shift
    if args[0].lower() in ["pagi", "siang", "malam"]:
        shift = args[0].lower()
        rest = args[1:]
    else:
        shift = data["active_shift"]
        rest = args

    if not rest:
        await update.message.reply_text("❌ Waktu dan pesan tidak boleh kosong.")
        return

    waktu = rest[0]
    pesan = " ".join(rest[1:]) if len(rest) > 1 else ""

    if not pesan:
        await update.message.reply_text("❌ Pesan reminder tidak boleh kosong.")
        return

    # Validasi format waktu
    try:
        h, m = map(int, waktu.split(":"))
        assert 0 <= h <= 23 and 0 <= m <= 59
    except:
        await update.message.reply_text("❌ Format waktu salah. Gunakan HH:MM, contoh: `09:00`", parse_mode="Markdown")
        return

    schedules = data["schedules"].get(shift, [])

    # Cek duplikat waktu
    existing_times = [w for w, _ in schedules]
    if waktu in existing_times:
        await update.message.reply_text(
            f"⚠️ Sudah ada reminder di jam {waktu} untuk shift {shift}.\n"
            f"Hapus dulu dengan `/hapus {shift} {waktu}` jika ingin mengganti.",
            parse_mode="Markdown"
        )
        return

    schedules.append((waktu, pesan))
    schedules.sort(key=lambda x: x[0])
    data["schedules"][shift] = schedules
    save_data(data)

    # Daftarkan ulang job jika shift ini sedang aktif
    if shift == data["active_shift"]:
        register_jobs(context.application, data)

    emoji = SHIFT_EMOJI[shift]
    await update.message.reply_text(
        f"✅ Reminder ditambahkan!\n"
        f"{emoji} Shift: *{shift.upper()}*\n"
        f"🕐 Waktu: *{waktu} WIB*\n"
        f"📝 Pesan: {pesan}",
        parse_mode="Markdown"
    )

# ─── COMMAND: /hapus ───────────────────────────────────────────
async def cmd_hapus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Format: /hapus [shift] HH:MM
    Contoh: /hapus pagi 09:00
            /hapus 10:30 (pakai shift aktif)
    """
    data = load_data()
    args = context.args

    if not args:
        await update.message.reply_text(
            "🗑️ *Format:*\n"
            "`/hapus [shift] HH:MM`\n\n"
            "*Contoh:*\n"
            "`/hapus pagi 09:00`\n"
            "`/hapus 10:30` (pakai shift aktif)\n\n"
            "Lihat daftar waktu dengan `/jadwal`",
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

    schedules = data["schedules"].get(shift, [])
    original_len = len(schedules)
    schedules = [(w, p) for w, p in schedules if w != waktu]

    if len(schedules) == original_len:
        await update.message.reply_text(
            f"❌ Tidak ada reminder jam *{waktu}* di shift *{shift}*.\n"
            f"Lihat daftar: `/jadwal {shift}`",
            parse_mode="Markdown"
        )
        return

    data["schedules"][shift] = schedules
    save_data(data)

    if shift == data["active_shift"]:
        register_jobs(context.application, data)

    await update.message.reply_text(
        f"✅ Reminder *{waktu} WIB* shift *{shift.upper()}* berhasil dihapus.",
        parse_mode="Markdown"
    )

# ─── COMMAND: /bantuan ─────────────────────────────────────────
async def cmd_bantuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 *Panduan Bot Reminder Shift*\n\n"
        "━━━━ SHIFT ━━━━\n"
        "`/shift` — lihat shift aktif\n"
        "`/shift pagi` — ganti ke shift pagi 🌅\n"
        "`/shift siang` — ganti ke shift siang 🌆\n"
        "`/shift malam` — ganti ke shift malam 🌙\n\n"
        "━━━━ JADWAL ━━━━\n"
        "`/jadwal` — lihat jadwal shift aktif\n"
        "`/jadwal pagi` — lihat jadwal shift pagi\n"
        "`/jadwal siang` — lihat jadwal shift siang\n"
        "`/jadwal malam` — lihat jadwal shift malam\n\n"
        "━━━━ TAMBAH ━━━━\n"
        "`/tambah pagi 09:00 Update laporan`\n"
        "`/tambah 10:30 Cek data` (pakai shift aktif)\n\n"
        "━━━━ HAPUS ━━━━\n"
        "`/hapus pagi 09:00`\n"
        "`/hapus 10:30` (pakai shift aktif)\n\n"
        "━━━━ LAINNYA ━━━━\n"
        "`/start` — tampilkan menu utama\n"
        "`/bantuan` — panduan ini\n\n"
        "💡 *Tips:* Semua member group bisa pakai semua perintah di atas."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── MAIN ──────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()

    # Daftarkan perintah
    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("shift",    cmd_shift))
    app.add_handler(CommandHandler("jadwal",   cmd_jadwal))
    app.add_handler(CommandHandler("tambah",   cmd_tambah))
    app.add_handler(CommandHandler("hapus",    cmd_hapus))
    app.add_handler(CommandHandler("bantuan",  cmd_bantuan))

    # Load data & daftarkan semua job saat bot start
    data = load_data()
    app.job_queue  # pastikan job queue aktif

    async def on_startup(app):
        data = load_data()
        register_jobs(app, data)
        # Set daftar perintah di menu bot
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
