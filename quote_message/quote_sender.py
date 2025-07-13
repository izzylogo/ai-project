import os
import time
import requests
from dotenv import load_dotenv
from openai import OpenAI
import schedule
from email.mime.text import MIMEText
import smtplib

# Load secrets
load_dotenv()

# OpenRouter setup
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# Telegram credentials
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Gmail credentials
SENDER_EMAIL = os.getenv("EMAIL_ADDRESS")
APP_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

def generate_quote():
    """Get a motivational quote from OpenRouter."""
    completion = client.chat.completions.create(
        model="deepseek/deepseek-r1-0528:free",
        messages=[{
            "role": "user",
            "content": "Give me a very short animation quote gotten from anime characters. It should not be in a list or in a very long form"
        }],
        extra_headers={
            "HTTP-Referer": "http://localhost",
            "X-Title": "DailyMotivationScript"
        }
    )
    return completion.choices[0].message.content.strip()

def send_to_telegram(message):
    """Send the quote to Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    response = requests.post(url, data=payload)
    if response.ok:
        print("✅ Quote sent to Telegram.")
    else:
        print("❌ Failed to send message:", response.text)


def send_email(quote):
    """Send the quote via Gmail with clean headers and body."""
    body = f"""
Hello,

Here's your anime quote for today:

"{quote}"

Have an inspired day!
"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "🌟 Your Daily Anime Quote"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Reply-To"] = SENDER_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(SENDER_EMAIL, APP_PASSWORD)
        smtp.send_message(msg)

    print("✅ Quote sent to Gmail.")



def job():
    """Generate and send the quote."""
    print("🔄 Generating quote...")
    quote = generate_quote()
    send_to_telegram(quote)
    send_email(quote)

# 🔁 Run once now for testing
if __name__ == "__main__":
    job()

    # 🔄 Keep for daily scheduling at 08:00 AM
    schedule.every().day.at("20:01").do(job)
    print("⏳ Waiting to send daily motivational quote at 08:00 AM...")

    while True:
        schedule.run_pending()
        time.sleep(60)
