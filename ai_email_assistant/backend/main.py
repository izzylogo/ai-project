from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from ai_utils import ask_ai_with_history
from email_utils import (
    send_email,
    read_emails,
    search_emails,
    delete_email,
    format_emails_as_text
)
import json
import re

app = FastAPI()

# Add CORS middleware to allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict this to just your frontend URL if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize global variables
chat_history = [
    {"role": "system", "content": (
        "You are a smart AI assistant. "
        "You help the user send, read, search, and delete emails. "
        "If the user asks for anything non-email-related, talk like you don't even know like you are an ai email agent, do research for the user and just assist out like a futuristic ai.\n\n"
        "To send an email:\n"
        "{\n"
        "  \"action\": \"send_email\",\n"
        "  \"to\": \"recipient@example.com\",\n"
        "  \"subject\": \"Subject line\",\n"
        "  \"body\": \"Email body\"\n"
        "}\n\n"
        "To read:\n"
        "{\n"
        "  \"action\": \"read_emails\",\n"
        "  \"filters\": {\"from\": \"john@example.com\", \"unread\": true, \"since\": \"2025-07-01\"}\n"
        "}\n\n"
        "To search:\n"
        "{\n"
        "  \"action\": \"search_emails\",\n"
        "  \"query\": \"Stripe payments\"\n"
        "}\n\n"
        "To delete:\n"
        "{\n"
        "  \"action\": \"delete_email\",\n"
        "  \"email_id\": \"12345\"\n"
        "}\n\n"
        "If the user asks a non-email-related question, respond with a friendly message like 'I am an email assistant. How can I assist you with emails today?' or just talk to the user like you're not an email assistant if they ask, but always remind him or her that your objective is to send emails, read emails, search emails, and delete emails."
    )}
]


# Global variables for managing email drafts and pending searches
pending_email_draft = None
pending_search_query = None  # Initialize the variable here

def extract_json(text):
    """Extract first JSON block from a string."""
    if "{" not in text:
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            json_str = json_str.replace("'", '"')
            return json.loads(json_str)
    return None


@app.post("/chat")
async def chat_endpoint(req: Request):
    global pending_email_draft, pending_search_query
    data = await req.json()
    user_input = data.get("message", "")

    # Handle pending send flow
    if pending_email_draft:
        if user_input.strip().lower() == "send":
            try:
                send_email(
                    pending_email_draft["to"],
                    pending_email_draft.get("subject", ""),
                    pending_email_draft["body"]
                )
                response_text = f"✅ Email sent to {pending_email_draft['to']}!"
                pending_email_draft = None
                return {"reply": response_text}
            except Exception as e:
                return {"reply": f"⚠️ Failed to send email: {e}"}
        elif user_input.strip().lower() == "edit":
            pending_email_draft = None
            return {"reply": "✍️ Draft cleared. What would you like the email to say instead?"}
        else:
            return {"reply": "💡 You have a draft pending. Type 'send' to send it or 'edit' to start over."}

    # Handle pending search flow
    if pending_search_query is not None:
        query = user_input.strip()
        results = search_emails(query, first_only=False, last_only=False)
        pending_search_query = None
        return {"reply": format_emails_as_text(results)}

    # Normal flow
    chat_history.append({"role": "user", "content": user_input})
    ai_reply = ask_ai_with_history(chat_history)

    if "⚠️ Error" in ai_reply:
        return {"reply": ai_reply}  # Display error message to user

    chat_history.append({"role": "assistant", "content": ai_reply})

    # Try to parse JSON for email actions
    email_data = extract_json(ai_reply)
    if email_data:
        action = email_data.get("action")
        if action == "send_email":
            if email_data.get("to") and email_data.get("body"):
                pending_email_draft = email_data
                return {"reply": (
                    f"📄 Draft ready:\n\n"
                    f"To: {email_data['to']}\n"
                    f"Subject: {email_data.get('subject', '')}\n"
                    f"Body: {email_data['body']}\n\n"
                    f"✅ Type 'send' to send this email, or 'edit' to change it."
                )}
            else:
                return {"reply": "⚠️ Missing recipient or body. Please clarify."}

        elif action == "read_emails":
            filters = email_data.get("filters", {})
            emails = read_emails(filters)
            return {"reply": format_emails_as_text(emails)}

        elif action == "search_emails":
            query = email_data.get("query", "")
            first_only = "first" in user_input.lower() or "oldest" in user_input.lower() or "sort" in email_data
            last_only = "last" in user_input.lower() or "newest" in email_data
            results = search_emails(query, first_only=first_only, last_only=last_only)

            if results:
                email_to_analyze = results[0]  # Pick the first result
                email_body = email_to_analyze.get("full_body", "")
                ai_response = ask_ai_with_history(chat_history + [{"role": "user", "content": email_body}])
                return {"reply": ai_response}

            return {"reply": "📭 No emails found."}

        elif action == "delete_email":
            uid = email_data.get("email_id")
            result = delete_email(uid)
            return {"reply": result}
    
    return {"reply": ai_reply}
