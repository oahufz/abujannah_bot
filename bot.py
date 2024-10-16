import telebot
import os
from dotenv import load_dotenv
import time
from requests.exceptions import RequestException
import csv
from datetime import datetime
import urllib3
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Désactiver les avertissements et ajuster les paramètres SSL
urllib3.disable_warnings()
urllib3.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'

# Désactiver complètement le proxy
os.environ['NO_PROXY'] = '*'
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

# Charger les variables d'environnement
load_dotenv()
os.environ['NO_PROXY'] = 'api.telegram.org'

# Récupérer le token du bot depuis les variables d'environnement
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))  # ID Telegram de l'administrateur
CHANNEL_ID = "@abujannah_alfaransi"  # ID du canal Telegram

# Créer l'instance du bot
bot = telebot.TeleBot(BOT_TOKEN)

# Configurer la session requests
session = requests.Session()
session.trust_env = False
telebot.apihelper.SESSION = session

# Nom du fichier CSV pour stocker les questions
QUESTIONS_FILE = 'questions.csv'

# Nom du fichier pour les logs de support
SUPPORT_LOGS_FILE = 'support_logs.csv'

# Fonction pour initialiser le fichier CSV s'il n'existe pas
def init_questions_file():
    if not os.path.exists(QUESTIONS_FILE):
        with open(QUESTIONS_FILE, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Numéro', 'Date', 'Question'])

# Fonction pour initialiser le fichier de logs de support
def init_support_logs_file():
    if not os.path.exists(SUPPORT_LOGS_FILE):
        with open(SUPPORT_LOGS_FILE, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Date', 'Utilisateur', 'Message', 'Réponse'])

# Fonction pour obtenir le dernier numéro de question
def get_last_question_number():
    if not os.path.exists(QUESTIONS_FILE):
        return 0
    with open(QUESTIONS_FILE, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        rows = list(reader)
        if len(rows) <= 1:  # Fichier vide ou contenant seulement l'en-tête
            return 0
        return int(rows[-1][0])  # Retourne le dernier numéro de question

# Fonction pour ajouter une question au fichier CSV
def add_question_to_file(number, question):
    with open(QUESTIONS_FILE, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([int(number), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), question])

# Fonction pour ajouter un log de support
def add_support_log(user, message, response=''):
    with open(SUPPORT_LOGS_FILE, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user, message, response])

# Fonction pour formater la question
def format_question(number, question):
    formatted_message = f"#{number:04d} Question posée :\n\n{question}"
    return formatted_message

# Fonction pour formater la réponse
def format_answer(number, question, answer):
    formatted_message = f"Question #{number:04d} :\n\n{question}\n\nRéponse :\n\n{answer}"
    return formatted_message

# Initialiser le fichier CSV et le compteur de questions
init_questions_file()
init_support_logs_file()
question_counter = get_last_question_number()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "As-Salam 'Alaykum, comment puis-je vous aider ?")

@bot.message_handler(commands=['question'])
def handle_question(message):
    global question_counter
    question = message.text.split('/question', 1)[-1].strip()

    if question:
        question_counter += 1
        add_question_to_file(question_counter, question)
        admin_message = format_question(question_counter, question)

        try:
            bot.send_message(ADMIN_ID, admin_message, parse_mode='HTML')
            print(f"Question envoyée à l'administrateur: Numéro {question_counter:04d}")
        except Exception as e:
            print(f"Erreur lors de l'envoi du message à l'administrateur: {e}")

        bot.reply_to(message, "Votre question a été envoyée, Jazak'Allah khayran.")
    else:
        bot.reply_to(message, "Veuillez poser votre question après la commande /question.")

@bot.message_handler(commands=['réponse'])
def handle_answer(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Désolé, seul l'administrateur peut utiliser cette commande.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "Format incorrect. Utilisez : /réponse [numéro] [réponse]")
        return

    question_number = parts[1].lstrip('#')  # Enlève le # si présent
    answer = parts[2]

    try:
        with open(QUESTIONS_FILE, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            questions = list(reader)

        question = next((q for q in questions if q[0] == question_number), None)
        if not question:
            bot.reply_to(message, f"Question numéro {question_number} non trouvée.")
            return

        formatted_answer = format_answer(int(question_number), question[2], answer)
        bot.send_message(CHANNEL_ID, formatted_answer, parse_mode='HTML')
        bot.reply_to(message, f"Réponse à la question #{question_number} envoyée sur le canal.")
    except Exception as e:
        bot.reply_to(message, f"Erreur lors du traitement de la réponse : {e}")
        print(f"Erreur détaillée : {e}")

@bot.message_handler(commands=['support'])
def handle_support(message):
    support_text = message.text.split('/support', 1)[-1].strip()
    if support_text:
        user = message.from_user.username or f"user_{message.from_user.id}"
        admin_message = f"Support - @{user}\n\n{support_text}"

        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(InlineKeyboardButton("Répondre", callback_data=f"reply_{message.from_user.id}"),
                   InlineKeyboardButton("Supprimer", callback_data="delete"))

        bot.send_message(ADMIN_ID, admin_message, reply_markup=markup)
        add_support_log(user, support_text)
        bot.reply_to(message, "Votre message de support a été envoyé à l'administrateur.")
    else:
        bot.reply_to(message, "Veuillez inclure votre message après la commande /support.")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "delete":
        bot.delete_message(call.message.chat.id, call.message.message_id)
    elif call.data.startswith("reply_"):
        user_id = call.data.split("_")[1]
        bot.answer_callback_query(call.id, "Veuillez entrer votre réponse:")
        bot.register_next_step_handler(call.message, send_reply, user_id)

def send_reply(message, user_id):
    try:
        bot.send_message(user_id, f"Réponse de l'administrateur:\n\n{message.text}")
        bot.reply_to(message, "Réponse envoyée avec succès.")
        add_support_log(f"user_{user_id}", "Réponse de l'admin", message.text)
    except Exception as e:
        bot.reply_to(message, f"Erreur lors de l'envoi de la réponse: {e}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.reply_to(message, "Pour poser une question, utilisez la commande /question suivie de votre question.")

if __name__ == "__main__":
    print("Le bot est en cours d'exécution...")
    print(f"Token du bot : {BOT_TOKEN[:5]}...")  # Affiche seulement les 5 premiers caractères pour des raisons de sécurité
    print(f"ID de l'administrateur : {ADMIN_ID}")
    print(f"ID du canal : {CHANNEL_ID}")
    print(f"Fichier de logs de support : {SUPPORT_LOGS_FILE}")
    while True:
        try:
            bot.polling(none_stop=True, interval=5, timeout=60)
        except RequestException as e:
            print(f"Erreur de connexion : {e}")
            time.sleep(30)
        except Exception as e:
            print(f"Une erreur inattendue s'est produite : {e}")
            time.sleep(30)