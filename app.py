from research import handle_message
from flask import Flask, request, render_template
from db import get_history, get_job


app = Flask(__name__)

@app.route("/")
def home():
    return render_template("chat.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_id = request.json["user_id"]
    user_message = request.json["message"]
    reply = handle_message(user_id, user_message)
    return {"reply": reply}

@app.route("/history/<chat_id>")
def history(chat_id):
    rows = get_history(chat_id, limit=100)
    messages = [{"role": role, "content": content} for role, content in rows]
    return {"messages": messages}

@app.route("/job/<chat_id>")
def job(chat_id):
    saved_job = get_job(chat_id)
    return {"job": saved_job}

if __name__ == "__main__":
    app.run(debug=True, port=5000)


