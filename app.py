from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slack_sdk import WebClient
import json, difflib, os

app = FastAPI()

# Load FAQ dataset
with open("faq.json", "r", encoding="utf-8") as f:
    faq_data = json.load(f)

# Slack bot setup
SLACK_BOT_TOKEN = "xoxb-5050737777652-9279963182803-o43f371Wwkk8lN3fuXGKiyXi"
slack_client = WebClient(token=SLACK_BOT_TOKEN)

# Slack events handler
@app.post("/slack/events")
async def slack_events(request: Request):
    payload = await request.json()

    if "challenge" in payload:
        return JSONResponse(content={"challenge": payload["challenge"]})

    if "event" in payload:
        event = payload["event"]
        text = event.get("text", "")
        channel_id = event.get("channel")

        # Remove @bot mentions like <@U1234>
        cleaned = ' '.join(word for word in text.split() if not word.startswith('<@'))

        # Find closest matching FAQ
        questions = [q["question"].lower() for q in faq_data]
        match = difflib.get_close_matches(cleaned.lower(), questions, n=1, cutoff=0.6)

        if match:
            answer = next((q["answer"] for q in faq_data if q["question"].lower() == match[0]), "Answer not found.")
        else:
            answer = "Sorry, I don’t know the answer to that yet!"
            with open("prompt_log.md", "a", encoding="utf-8") as log:
                log.write(f"Unanswered: {cleaned.strip()}\n")

        slack_client.chat_postMessage(channel=channel_id, text=answer)

    return JSONResponse(content={"ok": True})

# /chat endpoint for frontend use
@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        message = data.get("message", "").strip().lower()

        # Search for closest FAQ match
        questions = [q["question"].lower() for q in faq_data]
        match = difflib.get_close_matches(message, questions, n=1, cutoff=0.6)

        if match:
            answer = next((q["answer"] for q in faq_data if q["question"].lower() == match[0]), "Answer not found.")
        else:
            answer = "Sorry, I don’t know the answer to that yet!"
            with open("prompt_log.md", "a", encoding="utf-8") as log:
                log.write(f"Unanswered: {message}\n")

        return JSONResponse(content={"answer": answer})
    except Exception as e:
        return JSONResponse(content={"answer": "Error processing your message."}, status_code=400)

# ✅ Mount static files LAST to avoid API conflicts
current_dir = os.path.dirname(__file__)
static_dir = os.path.join(current_dir, "statics")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
