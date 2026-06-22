import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
from datetime import datetime
import threading
import time
import paramiko  # Yeni VPS'e SSH üzerinden script kurmak için gerekli

# =====================================================================
# 🛠️ DEĞİŞTİRMEN GEREKEN ALANLAR
# =====================================================================
API_TOKEN = '8826147048:AAFkZlZOKsS43RWrFXALU90XHO5sviSJkg0'  # @BotFather'dan aldığın bot tokenı
MASTER_PANEL_API = "https://vip.fastline-tm-belet-film.ru:8000/api"  # Marzban API linkin
MASTER_ADMIN_USERNAME = "komutan31"  # Ana panel süper admin kullanıcı adın
MASTER_ADMIN_PASSWORD = "admin"  # Ana panel süper admin şifren

# 🔐 BOTA ERİŞEBİLECEK TELEGRAM ID'LERİ
ALLOWED_TELEGRAM_IDS = [8359722718 ,7115611768] 
# =====================================================================

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

# --- GÜVENLİK FİLTRESİ ---
def is_authorized(message_or_call):
    if isinstance(message_or_call, telebot.types.CallbackQuery):
        user_id = message_or_call.from_user.id
    else:
        user_id = message_or_call.chat.id
    return user_id in ALLOWED_TELEGRAM_IDS

# --- MARZBAN API TOKEN ALMA ---
def get_marzban_token():
    try:
        login_url = f"{MASTER_PANEL_API}/admin/token"
        login_data = {"username": MASTER_ADMIN_USERNAME, "password": MASTER_ADMIN_PASSWORD}
        response = requests.post(login_url, data=login_data, timeout=10)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    except Exception:
        return None

# --- METADATA AYRIŞTIRICI ---
def parse_admin_meta(description_text):
    limit = "Sınırsız"
    expiry = "Sınırsız"
    if description_text and "limit:" in description_text:
        try:
            parts = description_text.split("|")
            for part in parts:
                if part.startswith("limit:"):
                    limit = part.split(":")[1]
                elif part.startswith("expiry:"):
                    expiry = part.split(":")[1]
        except Exception:
            pass
    return limit, expiry

# --- ANA MENÜ ---
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("👥 Panel Adminleri", callback_data="adminleri_listele"),
        InlineKeyboardButton("➕ Admin Ekle", callback_data="admin_ekle_basla")
    )
    markup.row(
        InlineKeyboardButton("🌐 Hostlar & IP", callback_data="hostlari_listele"),
        InlineKeyboardButton("🖥️ Nodları Yönet", callback_data="nodlari_listele")
    )
    return markup

@bot.message_handler(commands=['panel', 'start'])
def send_welcome(message):
    if not is_authorized(message):
        bot.send_message(message.chat.id, "❌ **YETKİSİZ ERİŞİM!**")
        return
    panel_text = "🛡️ **MARZBAN GELİŞMİŞ KONTROL PANELİ**\n\nSisteme başarıyla bağlanıldı. İşlem seçin 👇"
    bot.send_message(message.chat.id, panel_text, parse_mode="Markdown", reply_markup=main_menu())

# =====================================================================
# 🖥️ BÖLÜM 4: NODE (SUNUCU) YÖNETİMİ & OTOMATİK KURULUM VE IP DEĞİŞTİRME
# =====================================================================

# --- NODELARI LİSTELE ---
@bot.callback_query_handler(func=lambda call: call.data == "nodlari_listele")
def list_nodes(call):
    if not is_authorized(call): return
    chat_id = call.message.chat.id
    token = get_marzban_token()
    if not token:
        bot.answer_callback_query(call.id, "❌ API Hatası!", show_alert=True)
        return

    try:
        headers = {"Authorization": f"Bearer {token}"}
        # Marzban API'den tüm nodeları çekiyoruz
        nodes = requests.get(f"{MASTER_PANEL_API}/nodes", headers=headers, timeout=10).json()
        
        markup = InlineKeyboardMarkup()
        if isinstance(nodes, list):
            for node in nodes:
                if isinstance(node, dict):
                    node_id = node.get("id")
                    remark = node.get("name", f"Node #{node_id}")
                    status = "🟢" if node.get("status") == "connected" else "🔴"
                    # Callback verisinde ID'yi taşıyoruz
                    markup.add(InlineKeyboardButton(f"{status} {remark}", callback_data=f"node_detay_{node_id}"))
                    
        markup.add(InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data="ana_menuye_don"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                              text="🖥️ **Panelde Tanımlı Marzban Nodları:**\n\nDetayları görmek ve otomatik IP değiştirmek için bir node seçin:",
                              reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Nodlar listelenirken hata oluştu: `{str(e)}`")

# --- NODE DETAYINI GÖSTER ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("node_detay_"))
def show_node_details(call):
    if not is_authorized(call): return
    chat_id = call.message.chat.id
    node_id = call.data.split("_")[2]
    token = get_marzban_token()

    try:
        headers = {"Authorization": f"Bearer {token}"}
        node = requests.get(f"{MASTER_PANEL_API}/node/{node_id}", headers=headers, timeout=10).json()
        
        if not isinstance(node, dict) or "id" not in node:
            bot.send_message(chat_id, "❌ Node bilgileri panelden alınamadı.")
            return

        status_emoji = "🟢 Connected" if node.get("status") == "connected" else "🔴 Disconnected"
        
        detay_metni = (
            f"🖥️ **NODE BİLGİLERİ & DURUMU**\n\n"
            f"📌 **Node Adı (Remark):** `{node.get('name')}`\n"
            f"🆔 **Node ID:** `{node.get('id')}`\n"
            f"🔗 **Adres (IP/Domain):** `{node.get('address')}`\n"
            f"🔌 **Port:** `{node.get('port')}`\n"
            f"🔑 **API Port:** `{node.get('api_port')}`\n"
            f"⚡ **Durum:** {status_emoji}\n"
            f"📊 **Kullanım Oranı:** `{node.get('usage_ratio', 1)}`"
        )
        
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔄 Bu Node'un IP'sini Değiştir & Kur", callback_data=f"node_ip_degis_{node_id}"))
        markup.row(InlineKeyboardButton("⬅️ Node Listesine Dön", callback_data="nodlari_listele"))
        
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=detay_metni, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Node detayı işlenirken hata: `{str(e)}`")

# --- NODE IP DEĞİŞTİRME ADIM 1: YENİ IP İSTE ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("node_ip_degis_"))
def node_change_ip_start(call):
    if not is_authorized(call): return
    chat_id = call.message.chat.id
    node_id = call.data.split("_")[3]
    
    user_data[chat_id] = {"action_node_id": node_id}
    
    msg = bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                                text="🚀 **NODE IP & OTOMATİK KURULUM**\n\nLütfen bu node için atanacak **Yeni VPS IP Adresini** yazın:")
    bot.register_next_step_handler(msg, node_get_new_ip)

# --- NODE IP DEĞİŞTİRME ADIM 2: VPS ŞİFRESİ İSTE ---
def node_get_new_ip(message):
    if not is_authorized(message): return
    chat_id = message.chat.id
    new_ip = message.text.strip() if message.text else ""
    
    if not new_ip:
        bot.send_message(chat_id, "❌ Geçersiz IP girdiniz. İşlem iptal edildi.")
        return
        
    user_data[chat_id]['vps_new_ip'] = new_ip
    
    msg = bot.send_message(chat_id, f"🔑 `{new_ip}` sunucusuna SSH ile bağlanıp script kurabilmem için **root** şifresini yazın:")
    bot.register_next_step_handler(msg, node_execute_migration)

# --- NODE IP DEĞİŞTİRME ADIM 3: SSH BAGLANTISI, SCRIPT KURULUMU VE PANEL GÜNCELLEME ---
def node_execute_migration(message):
    if not is_authorized(message): return
    chat_id = message.chat.id
    vps_password = message.text.strip() if message.text else ""
    
    if not vps_password:
        bot.send_message(chat_id, "❌ Şifre boş olamaz. İşlem iptal edildi.")
        return

    node_id = user_data[chat_id].get("action_node_id")
    new_ip = user_data[chat_id].get("vps_new_ip")
    
    token = get_marzban_token()
    if not token:
        bot.send_message(chat_id, "❌ Panel API bağlantısı kurulamadı.")
        return

    status_msg = bot.send_message(chat_id, f"⏳ **1/3** `{new_ip}` sunucusuna SSH ile bağlanılıyor...")

    # --- SÜREÇ BAŞLANGICI ---
    try:
        # 1. Aşama: Yeni sunucuya SSH ile bağlanıp kurulum scriptini çalıştırma
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Sunucuya bağlan (varsayılan port 22, kullanıcı root)
        ssh.connect(hostname=new_ip, port=22, username="root", password=vps_password, timeout=15)
        
        bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, 
                              text=f"⚙️ **2/3** SSH bağlantısı başarılı. Marzban Node scripti kuruluyor...\n_(Bu işlem sunucu hızına göre 30-40 sn sürebilir)_")
        
        # İstediğin kurulum komutunu arka arkaya yürütüyoruz
        install_cmd = 'sudo bash -c "$(curl -sL https://github.com/Gozargah/Marzban-scripts/raw/master/marzban-node.sh)" @ install'
        stdin, stdout, stderr = ssh.exec_command(install_cmd, timeout=90)
        
        # Komutun bitmesini bekle
        exit_status = stdout.channel.recv_exit_status()
        ssh.close()
        
        if exit_status != 0:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, 
                                  text=f"❌ **HATA:** Sunucuda script kurulumu başarısız oldu! Exit kodu: `{exit_status}`")
            return

        # 2. Aşama: Paneldeki eski Node'un bilgilerini çekip sadece IP alanını güncelleme
        bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, 
                              text=f"📥 **3/3** Kurulum tamamlandı. Marzban Master paneline yeni IP işleniyor...")
        
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        current_node = requests.get(f"{MASTER_PANEL_API}/node/{node_id}", headers=headers, timeout=10).json()
        
        # Mevcut ayarları bozmadan sadece adresi değiştiriyoruz
        payload = {
            "name": current_node.get("name"),
            "address": new_ip,
            "port": current_node.get("port", 62050),
            "api_port": current_node.get("api_port", 62051),
            "usage_ratio": current_node.get("usage_ratio", 1)
        }
        
        # PUT isteği ile node güncelleme
        update_res = requests.put(f"{MASTER_PANEL_API}/node/{node_id}", json=payload, headers=headers, timeout=10)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Nodlara Dön", callback_data="nodlari_listele"))
        
        if update_res.status_code in [200, 204]:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, 
                                  text=f"✅ **NODE BAŞARIYLA TAŞINDI VE BAĞLANDI!**\n\n• **Yeni IP:** `{new_ip}`\n• **Script Durumu:** Kuruldu 🟢\n• **Panel Bağlantısı:** Aktif (Connected) ⚡", 
                                  reply_markup=markup)
        else:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, 
                                  text=f"❌ Script kuruldu fakat panel IP'si güncellenemedi. API Kodu: `{update_res.status_code}`", 
                                  reply_markup=markup)

    except paramiko.AuthenticationException:
        bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text="❌ **SSH HATASI:** Giriş başarısız. Root şifresi yanlış olabilir.")
    except Exception as e:
        bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=f"❌ **İŞLEM BAŞARISIZ OLDU:** `{str(e)}`")


# =====================================================================
# 👥 BÖLÜM 1 & 2: PANEL ADMİNLERİ EKLEME VE SİLME SÜREÇLERİ
# =====================================================================

@bot.callback_query_handler(func=lambda call: call.data == "admin_ekle_basla")
def add_admin_start(call):
    if not is_authorized(call): return
    chat_id = call.message.chat.id
    user_data[chat_id] = {}
    msg = bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                                text="👤 **ADMİN EKLE**\n\nOluşturulacak yeni adminin **Kullanıcı Adını (Username)** yazın:")
    bot.register_next_step_handler(msg, get_new_admin_username)

def get_new_admin_username(message):
    if not is_authorized(message): return
    chat_id = message.chat.id
    username = message.text.strip() if message.text else ""
    if not username:
        bot.send_message(chat_id, "❌ Geçersiz kullanıcı adı. İptal edildi.")
        return
    user_data[chat_id]['new_admin_username'] = username
    msg = bot.send_message(chat_id, f"🔑 `{username}` admini için bir **Şifre (Password)** belirleyin:")
    bot.register_next_step_handler(msg, get_new_admin_password)

def get_new_admin_password(message):
    if not is_authorized(message): return
    chat_id = message.chat.id
    password = message.text.strip() if message.text else ""
    if not password:
        bot.send_message(chat_id, "❌ Geçersiz şifre. İptal edildi.")
        return
    user_data[chat_id]['new_admin_password'] = password
    msg = bot.send_message(chat_id, f"📊 `{user_data[chat_id]['new_admin_username']}` bu panelde **en fazla kaç kullanıcı** oluşturabilsin? (Örn: 50):")
    bot.register_next_step_handler(msg, get_new_admin_limit)

def get_new_admin_limit(message):
    if not is_authorized(message): return
    chat_id = message.chat.id
    limit = message.text.strip() if message.text else ""
    if not limit.isdigit():
        bot.send_message(chat_id, "❌ Lütfen sadece sayısal bir limit girin. İptal edildi.")
        return
    user_data[chat_id]['new_admin_limit'] = limit
    msg = bot.send_message(chat_id, f"📅 Panel bitiş süresini girin.\nFormat tam olarak şu şekilde olmalıdır: **GG.AA.YYYY** (Örn: 23.07.2026):")
    bot.register_next_step_handler(msg, execute_admin_create)

def execute_admin_create(message):
    if not is_authorized(message): return
    chat_id = message.chat.id
    expiry_date = message.text.strip() if message.text else ""
    
    try:
        datetime.strptime(expiry_date, "%d.%m.%Y")
    except ValueError:
        bot.send_message(chat_id, "❌ Tarih formatı hatalı (GG.AA.YYYY olmalı). İşlem iptal edildi.")
        return

    username = user_data[chat_id].get('new_admin_username')
    password = user_data[chat_id].get('new_admin_password')
    limit = user_data[chat_id].get('new_admin_limit')
    
    token = get_marzban_token()
    if not token:
        bot.send_message(chat_id, "❌ API bağlantısı kurulamadı.")
        return

    status_msg = bot.send_message(chat_id, "⏳ Veriler panele kaydediliyor...")

    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        meta_description = f"limit:{limit}|expiry:{expiry_date}"
        
        payload = {
            "username": username,
            "password": password,
            "is_sudo": False,
            "description": meta_description
        }
        
        res = requests.post(f"{MASTER_PANEL_API}/admin", json=payload, headers=headers, timeout=10)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data="ana_menuye_don"))
        
        if res.status_code in [200, 201]:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id,
                                  text=f"✅ **ADMİN BAŞARIYLA OLUŞTU!**\n\n• **Kullanıcı Adı:** `{username}`\n• **Şifre:** `{password}`\n• **Kullanıcı Limiti:** `{limit}` adet\n• **Bitiş Süresi:** `{expiry_date}` 📅\n• **Sudo Yetkisi:** `Hayır (n)` 🟢",
                                  reply_markup=markup, parse_mode="Markdown")
        else:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=f"❌ Hata oluştu. Kod: {res.status_code}", reply_markup=markup)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Sistem hatası: `{str(e)}`")

@bot.callback_query_handler(func=lambda call: call.data == "adminleri_listele")
def list_admins(call):
    if not is_authorized(call): return
    chat_id = call.message.chat.id
    token = get_marzban_token()
    if not token:
        bot.answer_callback_query(call.id, "❌ API Hatası!", show_alert=True)
        return

    try:
        headers = {"Authorization": f"Bearer {token}"}
        admins = requests.get(f"{MASTER_PANEL_API}/admins", headers=headers, timeout=10).json()
        
        markup = InlineKeyboardMarkup()
        for admin in admins:
            if isinstance(admin, dict):
                username = admin.get("username")
                role_emoji = "👑" if admin.get("is_sudo") else "👨‍💻"
                markup.add(InlineKeyboardButton(f"{role_emoji} {username}", callback_data=f"adm_detay_{username}"))
            
        markup.add(InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data="ana_menuye_don"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                              text="👥 **Panelde Kayıtlı Tüm Adminler:**\n\nDetayları, limitleri ve bitiş sürelerini görmek için seçin:",
                              reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Liste alınamadı: `{str(e)}`")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_detay_"))
def show_admin_details(call):
    if not is_authorized(call): return
    chat_id = call.message.chat.id
    target_username = call.data.split("_")[2]
    token = get_marzban_token()

    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        admins_list = requests.get(f"{MASTER_PANEL_API}/admins", headers=headers, timeout=10).json()
        target_admin_data = next((a for a in admins_list if isinstance(a, dict) and a.get("username") == target_username), {})
        
        description = target_admin_data.get("description", "")
        allowed_limit, expiry_date = parse_admin_meta(description)
        
        response = requests.get(f"{MASTER_PANEL_API}/users", headers=headers, timeout=10)
        all_users = response.json().get("users", []) if response.status_code == 200 else []
        
        admin_users = []
        total_bytes = 0
        
        for u in all_users:
            if isinstance(u, dict):
                admin_info = u.get("admin")
                if admin_info and isinstance(admin_info, dict) and admin_info.get("username") == target_username:
                    admin_users.append(u)
                    total_bytes += u.get("used_traffic", 0) if u.get("used_traffic") else 0

        user_count = len(admin_users)
        total_gb = round(total_bytes / (1024 ** 3), 2)
        
        user_names_list = ""
        for idx, u in enumerate(admin_users, 1):
            if isinstance(u, dict):
                user_names_list += f"{idx}. `{u.get('username')}`\n"
        
        if not user_names_list:
            user_names_list = "_Bu admin henüz hiç kullanıcı oluşturmamış._"

        detay_metni = (
            f"👤 **ADMİN İSTATİSTİKLERİ: {target_username}**\n\n"
            f"📊 **Oluşturulan Kullanıcı:** {user_count} / {allowed_limit} Adet\n"
            f"📉 **Toplam Trafik Tüketimi:** {total_gb} GB\n"
            f"📅 **Panel Bitiş Süresi:** `{expiry_date}` 🕒\n\n"
            f"📋 **Oluşturulan Kullanıcı Listesi:**\n{user_names_list}"
        )
        
        markup = InlineKeyboardMarkup()
        if target_username != MASTER_ADMIN_USERNAME:
            markup.row(InlineKeyboardButton("🗑️ Admini ve TÜM Kullanıcılarını Sil", callback_data=f"adm_sil_{target_username}"))
        markup.row(InlineKeyboardButton("⬅️ Admin Listesine Dön", callback_data="adminleri_listele"))
        
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=detay_metni, reply_markup=markup, parse_mode="Markdown")
                              
    except Exception as e:
        bot.send_message(chat_id, f"❌ Detay işlenirken hata: `{str(e)}`")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_sil_"))
def delete_admin_execute(call):
    if not is_authorized(call): return
    chat_id = call.message.chat.id
    target_username = call.data.split("_")[2]
    token = get_marzban_token()

    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        users_response = requests.get(f"{MASTER_PANEL_API}/users", headers=headers, timeout=10)
        if users_response.status_code == 200:
            all_users = users_response.json().get("users", [])
            for u in all_users:
                if isinstance(u, dict):
                    admin_info = u.get("admin")
                    if admin_info and isinstance(admin_info, dict) and admin_info.get("username") == target_username:
                        requests.delete(f"{MASTER_PANEL_API}/user/{u.get('username')}", headers=headers, timeout=5)

        res = requests.delete(f"{MASTER_PANEL_API}/admin/{target_username}", headers=headers, timeout=10)
        
        if res.status_code in [200, 204]:
            bot.answer_callback_query(call.id, f"🗑️ {target_username} ve tüm kullanıcıları temizlendi!", show_alert=True)
            list_admins(call)
        else:
            bot.answer_callback_query(call.id, "❌ Yetki yetersiz veya işlem başarısız.", show_alert=True)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Hata: `{str(e)}`")

# =====================================================================
# 🌐 BÖLÜM 3: HOSTLAR VE TOPLU IP DEĞİŞTİRME YÖNETİMİ
# =====================================================================

@bot.callback_query_handler(func=lambda call: call.data == "hostlari_listele")
def list_hosts(call):
    if not is_authorized(call): return
    chat_id = call.message.chat.id
    token = get_marzban_token()
    if not token:
        bot.answer_callback_query(call.id, "❌ API bağlantısı başarısız!", show_alert=True)
        return

    try:
        headers = {"Authorization": f"Bearer {token}"}
        hosts_data = requests.get(f"{MASTER_PANEL_API}/hosts", headers=headers, timeout=10).json()
        host_detay_metni = "🌐 **MEVCUT PANEL HOSTLARI VE GİRİŞLERİ**\n\n"
        
        if isinstance(hosts_data, dict):
            for inbound, hosts in hosts_data.items():
                host_detay_metni += f"🔹 **İnbound Grubu:** `{inbound}`\n"
                if not hosts or not isinstance(hosts, list):
                    host_detay_metni += " └ ⚠️ _Bu gruba tanımlı host bulunmuyor._\n\n"
                    continue
                for h in hosts:
                    if isinstance(h, dict):
                        host_detay_metni += (
                            f" ├ 📍 Remark: `{h.get('remark', 'Yok')}`\n"
                            f" ├ 🔗 Adres (IP/Domain): `{h.get('address')}`\n"
                            f" └ 🔌 Port: `{h.get('port', 'Default')}`\n"
                        )
                host_detay_metni += "\n"
            
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔄 Tüm Hostların IP'sini Değiştir", callback_data="toplu_ip_degistir_istek"))
        markup.row(InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data="ana_menuye_don"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=host_detay_metni, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Host hatası: `{str(e)}`")

@bot.callback_query_handler(func=lambda call: call.data == "toplu_ip_degistir_istek")
def request_new_ip_for_hosts(call):
    if not is_authorized(call): return
    chat_id = call.message.chat.id
    msg = bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="🚀 **TOPLU HOST IP GÜNCELLEME**\n\nLütfen yeni **IP Adresini** yazın:")
    bot.register_next_step_handler(msg, execute_bulk_ip_change)

def execute_bulk_ip_change(message):
    if not is_authorized(message): return
    chat_id = message.chat.id
    new_ip = message.text.strip() if message.text else ""
    if not new_ip: return
        
    token = get_marzban_token()
    status_msg = bot.send_message(chat_id, "⏳ İnbound listeleri güncelleniyor...")
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        hosts_data = requests.get(f"{MASTER_PANEL_API}/hosts", headers=headers, timeout=10).json()
        
        updated_hosts_data = {}
        if isinstance(hosts_data, dict):
            for inbound, hosts in hosts_data.items():
                updated_hosts_data[inbound] = []
                if isinstance(hosts, list):
                    for h in hosts:
                        if isinstance(h, dict):
                            h['address'] = new_ip
                            updated_hosts_data[inbound].append(h)
                
        res = requests.put(f"{MASTER_PANEL_API}/hosts", json=updated_hosts_data, headers=headers, timeout=10)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data="ana_menuye_don"))
        
        if res.status_code in [200, 204]:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=f"✅ **İŞLEM TAMAMLANDI!**\n\nTüm host IP'leri başarıyla `{new_ip}` olarak güncellendi! ⚡", reply_markup=markup)
        else:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text="❌ Güncelleme API tarafından reddedildi.", reply_markup=markup)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Hata: {str(e)}")

# =====================================================================
# 🕒 ARKA PLAN SÜREÇ MOTORU: OTOMATİK ZAMANLI SİLME (CRON THREAD)
# =====================================================================
def auto_expiry_cron_job():
    while True:
        token = get_marzban_token()
        if token:
            try:
                headers = {"Authorization": f"Bearer {token}"}
                admins = requests.get(f"{MASTER_PANEL_API}/admins", headers=headers, timeout=10).json()
                today_str = datetime.now().strftime("%d.%m.%Y")
                today_dt = datetime.strptime(today_str, "%d.%m.%Y")
                
                for admin in admins:
                    if isinstance(admin, dict):
                        username = admin.get("username")
                        description = admin.get("description", "")
                        
                        if username == MASTER_ADMIN_USERNAME: continue
                        
                        _, expiry_str = parse_admin_meta(description)
                        
                        if expiry_str != "Sınırsız":
                            try:
                                expiry_dt = datetime.strptime(expiry_str, "%d.%m.%Y")
                                if today_dt >= expiry_dt:
                                    print(f"🕒 [CRON] {username} süresi doldu. Temizlik başlatılıyor...")
                                    
                                    users_res = requests.get(f"{MASTER_PANEL_API}/users", headers=headers, timeout=10).json()
                                    all_users = users_res.get("users", [])
                                    for u in all_users:
                                        if isinstance(u, dict):
                                            admin_info = u.get("admin")
                                            if admin_info and isinstance(admin_info, dict) and admin_info.get("username") == username:
                                                requests.delete(f"{MASTER_PANEL_API}/user/{u.get('username')}", headers=headers, timeout=5)
                                    
                                    requests.delete(f"{MASTER_PANEL_API}/admin/{username}", headers=headers, timeout=10)
                                    print(f"🗑️ [CRON] {username} ve tüm kullanıcıları başarıyla uçuruldu.")
                            except Exception as cron_err:
                                print(f"Cron admin ayrıştırma hatası: {str(cron_err)}")
            except Exception as global_cron_err:
                print(f"Global cron hatası: {str(global_cron_err)}")
        
        time.sleep(86400) # 24 saatte bir çalışır

# =====================================================================
# 🔄 ASİSTAN HANDLERLAR VE BAŞLATICI
# =====================================================================
@bot.callback_query_handler(func=lambda call: call.data == "ana_menuye_don")
def back_to_main(call):
    if not is_authorized(call): return
    panel_text = "🛡️ **MARZBAN GELİŞMİŞ KONTROL PANELİ**\n\nSisteme başarıyla bağlanıldı. İşlem seçin 👇"
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=panel_text, reply_markup=main_menu(), parse_mode="Markdown")

if __name__ == '__main__':
    cron_thread = threading.Thread(target=auto_expiry_cron_job, daemon=True)
    cron_thread.start()
    
    print("🤖 Marzban Akıllı Yönetim Botu ve Zamanlayıcı Motoru aktif!")
    bot.infinity_polling()
