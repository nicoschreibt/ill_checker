import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL
import hashlib
from datetime import datetime
import os
import json

sender_email = SENDER_EMAIL
sender_password = SENDER_PASSWORD
receiver_email = RECEIVER_EMAIL

# Websites
url_wg_ill = "https://wg-ill.ch/de/angebot"
url_soca = "https://www.soca.ch/kopie-von-meldung-vollstand"

# Datei zur Speicherung der Hashes
HASHES_FILE = "website_hashes.json"

# Liste der Wohnungen, die überprüft werden sollen
wohnungen_zu_pruefen = [
    "2 Z-WHG",
    "3 Z-WHG",
    "4 Z-WHG",
    "6 Z-WHG",
    "3 Z-REFH",
    "4 Z-REFH",
    "5 Z-REFH"
]


def load_hashes():
    """
    Lädt die gespeicherten Hashes der Websites.
    """
    if os.path.exists(HASHES_FILE):
        try:
            with open(HASHES_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_hashes(hashes):
    """
    Speichert die Hashes der Websites.
    """
    with open(HASHES_FILE, 'w') as f:
        json.dump(hashes, f)


def get_content_hash(content):
    """
    Berechnet den SHA256-Hash des Website-Inhalts.
    """
    return hashlib.sha256(content.encode()).hexdigest()


def send_email(subject, body):
    """
    Sendet eine Email.
    """
    try:
        # SMTP-Server verbindung mit Gmail
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, sender_password)
        
        # Email erstellen
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain", "utf-8"))
        
        # Email senden
        server.sendmail(sender_email, receiver_email, message.as_string())
        server.quit()
        
        print(f"✓ Email erfolgreich an {receiver_email} gesendet!")
        
    except Exception as e:
        print(f"✗ Fehler beim Versenden der Email: {e}")
        print("Überprüfe bitte die Email-Konfiguration!")


def send_wg_ill_email(gefundene_wohnungen, wohnung_frei):
    """
    Sendet eine Email, wenn Wohnungen verfügbar sind.
    """
    # Email-Inhalt erstellen
    subject = "🏠 Wohnungen verfügbar bei WG-ill!"
    
    body = f"""Hallo Nicolas,

gute Nachrichten! Es gibt verfügbare Wohnungen bei WG-ill!

Status: {wohnung_frei}

Verfügbare Wohnungen:
"""
    
    for w in gefundene_wohnungen:
        if "geschlossen" not in w['status'].lower():
            body += f"\n- {w['typ']}: {w['status']}"
    
    body += f"""

Schau bitte auf der Website nach:
https://wg-ill.ch/de/angebot

Viele Grüße,
WG-ill Checker
"""
    
    send_email(subject, body)


def send_soca_email():
    """
    Sendet eine Email, wenn sich etwas bei Soca geändert hat.
    """
    subject = "📢 Änderung bei Soca entdeckt!"
    
    body = """Hallo Nicolas,

es gibt eine Änderung bei Soca!

Schau bitte auf der Website nach:
https://www.soca.ch/kopie-von-meldung-vollstand

Viele Grüße,
WG-ill Checker
"""
    
    send_email(subject, body)


# Datum am Anfang ausdrucken
current_date = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
print(f"\n{'='*50}")
print(f"Überprüfung gestartet: {current_date}")
print(f"{'='*50}\n")

# Hashes laden
stored_hashes = load_hashes()

try:
    # ========== WG-ILL ÜBERPRÜFUNG ==========
    print("Überprüfe WG-ill Website...")
    response = requests.get(url_wg_ill)
    response.raise_for_status()
    
    # HTML parsen
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Alle Tabellen suchen
    tables = soup.find_all('table')
    
    # Überprüfen, ob alle Wohnungen "geschlossen" sind
    alle_geschlossen = True
    gefundene_wohnungen = []
    
    for table in tables:
        rows = table.find_all('tr')
        
        for row in rows:
            cells = row.find_all('td')
            
            if len(cells) >= 3:
                # Erste Spalte (Wohnungstyp)
                wohnungstyp = cells[0].get_text(strip=True)
                # Dritte Spalte (Status)
                status = cells[2].get_text(strip=True)
                
                # Überprüfen, ob diese Wohnung in unserer Liste ist
                for wohnung in wohnungen_zu_pruefen:
                    if wohnung.lower() in wohnungstyp.lower():
                        gefundene_wohnungen.append({
                            'typ': wohnungstyp,
                            'status': status
                        })
                        
                        # Wenn der Status nicht "geschlossen" ist, setze alle_geschlossen auf False
                        if "geschlossen" not in status.lower():
                            alle_geschlossen = False
                        
                        print(f"  Gefunden: {wohnungstyp} - {status}")
    
    # Variable wohnung_frei setzen
    wohnung_frei = "geschlossen" if alle_geschlossen else "offen"
    
    print(f"\n  Alle überprüften Wohnungen sind geschlossen: {alle_geschlossen}")
    print(f"  wohnung_frei = '{wohnung_frei}'")
    
    # Email senden, wenn Wohnungen verfügbar sind
    if wohnung_frei != "geschlossen":
        send_wg_ill_email(gefundene_wohnungen, wohnung_frei)
    else:
        print("  → Keine Änderungen, keine Email gesendet.")
    
    # ========== SOCA ÜBERPRÜFUNG ==========
    print("\n\nÜberprüfe Soca Website...")
    response_soca = requests.get(url_soca)
    response_soca.raise_for_status()
    
    # Content-Hash berechnen
    current_hash = get_content_hash(response_soca.text)
    old_hash = stored_hashes.get("soca", None)
    
    if old_hash is None:
        print("  → Erste Überprüfung (Hash wird gespeichert)")
        stored_hashes["soca"] = current_hash
    elif current_hash == old_hash:
        print("  → Keine Änderungen seit der letzten Überprüfung")
    else:
        print("  → Änderung entdeckt!")
        send_soca_email()
        stored_hashes["soca"] = current_hash
    
    # Hashes speichern
    save_hashes(stored_hashes)
    
    print(f"\n{'='*50}")
    print(f"Überprüfung abgeschlossen: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"{'='*50}\n")

except requests.exceptions.RequestException as e:
    print(f"✗ Fehler beim Abrufen der Website: {e}")
except Exception as e:
    print(f"✗ Ein Fehler ist aufgetreten: {e}")
