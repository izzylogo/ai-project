import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import imaplib
import email
from email.header import decode_header

load_dotenv()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def connect_imap():
    """Connect to the IMAP server."""
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    return imap

def send_email(to_email, subject, body):
    """Send email via Gmail SMTP."""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

    return f"✅ Email sent to {to_email}."

def read_emails(filters):
    """Read emails with optional filters like from, unread, since."""
    imap = connect_imap()
    imap.select("inbox")

    # Build search criteria
    criteria = []
    if filters.get("from"):
        criteria.append(f'FROM "{filters["from"]}"')
    if filters.get("unread"):
        criteria.append('UNSEEN')
    if filters.get("since"):
        criteria.append(f'SINCE "{filters["since"]}"')
    if not criteria:
        criteria = ["ALL"]

    search_query = " ".join(criteria)
    status, messages = imap.search(None, *criteria)

    email_data = []
    if status == "OK":
        for num in messages[0].split()[-5:]:  # get last 5 matching emails
            _, msg_data = imap.fetch(num, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = decode_header(msg["Subject"])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode()
                    from_ = msg.get("From")
                    date_ = msg.get("Date")
                    snippet = ""
                    full_body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                full_body = part.get_payload(decode=True).decode(errors="ignore")
                                snippet = full_body[:100]
                                break
                    else:
                        full_body = msg.get_payload(decode=True).decode(errors="ignore")
                        snippet = full_body[:100]
                    email_data.append({
                        "uid": num.decode(),
                        "subject": subject,
                        "from": from_,
                        "date": date_,
                        "snippet": snippet,
                        "full_body": full_body  # Add the full body here
                    })
    imap.logout()
    return email_data

def delete_email(email_uid):
    """Delete an email by its IMAP UID."""
    imap = connect_imap()
    imap.select("inbox")
    imap.store(email_uid, '+FLAGS', '\\Deleted')
    imap.expunge()
    imap.logout()
    return f"🗑️ Deleted email with UID {email_uid}."

def search_emails(query, first_only=False, last_only=False):
    """Search emails by subject keyword."""
    imap = connect_imap()
    imap.select("inbox")
    status, messages = imap.search(None, "ALL")
    results = []

    if status == "OK":
        uids = messages[0].split()
        if first_only:
            uids = reversed(uids)  # oldest first
        else:
            uids = uids[::-1]  # newest first

        for num in uids:
            _, msg_data = imap.fetch(num, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = decode_header(msg["Subject"])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode()
                    if query.lower() in subject.lower():
                        from_ = msg.get("From")
                        date_ = msg.get("Date")
                        snippet = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    snippet = part.get_payload(decode=True).decode(errors="ignore")[:100]
                                    break
                        else:
                            snippet = msg.get_payload(decode=True).decode(errors="ignore")[:100]
                        results.append({
                            "uid": num.decode(),
                            "subject": subject,
                            "from": from_,
                            "date": date_,
                            "snippet": snippet
                        })
                        if first_only or last_only:
                            imap.logout()
                            return results
    imap.logout()
    return results

def format_emails_as_text(emails):
    """Format list of emails into a pretty text block for chat."""
    if not emails:
        return "📭 No emails found."
    lines = []
    for idx, email in enumerate(emails, 1):
        lines.append(f"{idx}. 📧 Subject: {email['subject']} - From: {email['from']} on {email['date']}\n> {email['snippet']}")
    return "\n\n".join(lines)
