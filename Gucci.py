from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests

app = FastAPI()

# 🔴 BURAYI DOLDUR
BOT_TOKEN = "8834909037:AAFISe23LU4TWF3H-0McwePwtJiruPwSdqk"
CHAT_ID = "8359722718"


class Form(BaseModel):
    field1: str
    field2: str


# 🌐 Site (2 inputlu sayfa)
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Form</title>
    </head>
    <body style="font-family:Arial;text-align:center;margin-top:100px;">

        <h2>Mesaj Gönder</h2>

        <input id="f1" placeholder="1. kutu"><br><br>
        <input id="f2" placeholder="2. kutu"><br><br>

        <button onclick="send()">Gönder</button>

        <script>
            function send(){
                fetch("/send", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        field1: document.getElementById("f1").value,
                        field2: document.getElementById("f2").value
                    })
                });

                alert("Gönderildi");
            }
        </script>

    </body>
    </html>
    """


# 📩 Telegram'a gönderme kısmı
@app.post("/send")
def send(data: Form):

    text = f"""
📩 Yeni Form Mesajı

🔹 Kutu 1: {data.field1}
🔹 Kutu 2: {data.field2}
"""

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    })

    return {"status": "ok"}
