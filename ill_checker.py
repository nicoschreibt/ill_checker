import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json
try:
    # bevorzugter Import, wenn `config.py` im selben Paket/Folder liegt
    from ill_checker.config import SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL
except Exception:
    # fallback: config.py im Projektroot oder im PYTHONPATH
    from config import SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL

# Website URL
url = "https://wg-ill.ch/de/angebot"

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

# persistent state file to track which apartments we've already notified about
STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Warnung: konnte state.json nicht speichern: {e}")


def send_email(gefundene_wohnungen, wohnung_frei):
    """Sendet eine Email mit den angegebenen Wohnungen.

    `gefundene_wohnungen` sollte eine Liste von Dicts mit 'typ' und 'status' sein.
    """
    subject = "🏠 Wohnungen verfügbar bei WG-ill!"

    body = f"""Hallo Nicolas,

gute Nachrichten! Es gibt verfügbare Wohnungen bei WG-ill!

Status: {wohnung_frei}

Verfügbare Wohnungen:
"""

    for w in gefundene_wohnungen:
        body += f"\n- {w['typ']}: {w['status']}"

    body += f"""

Schau bitte auf der Website nach:
https://wg-ill.ch/de/angebot

Viele Grüße,
WG-ill Checker
"""

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)

        message = MIMEMultipart()
        message["From"] = SENDER_EMAIL
        message["To"] = RECEIVER_EMAIL
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain", "utf-8"))

        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, message.as_string())
        server.quit()

        print(f"\n✓ Email erfolgreich an {RECEIVER_EMAIL} gesendet!")
    except Exception as e:
        print(f"\n✗ Fehler beim Versenden der Email: {e}")
        print("Überprüfe bitte die Email-Konfiguration!")


try:
    # Website abrufen
    response = requests.get(url)
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
                        
                        print(f"Gefunden: {wohnungstyp} - {status}")
    
    # Variable wohnung_frei setzen
    wohnung_frei = "geschlossen" if alle_geschlossen else "offen"
    
    print("\n" + "="*50)
    print(f"Alle überprüften Wohnungen sind geschlossen: {alle_geschlossen}")
    print(f"wohnung_frei = '{wohnung_frei}'")
    print("="*50)
    
    # Zusammenfassung ausgeben
    if gefundene_wohnungen:
        print("\nZusammenfassung der gefundenen Wohnungen:")
        for w in gefundene_wohnungen:
            print(f"  - {w['typ']}: {w['status']}")
    else:
        print("\nWarnung: Keine der gesuchten Wohnungen wurden gefunden!")
        print("Die Seitenstruktur könnte sich geändert haben.")
    
    # Email senden, aber nur für neue offene Wohnungen (einmalig)
    if wohnung_frei != "geschlossen":
        state = load_state()

        # Liste der aktuell offenen Wohnungen
        open_wohnungen = [w for w in gefundene_wohnungen if "geschlossen" not in w['status'].lower()]

        # Nur die Wohnungen benachrichtigen, die noch nicht in state als benachrichtigt markiert wurden
        to_notify = [w for w in open_wohnungen if not state.get(w['typ'], False)]

        if to_notify:
            send_email(to_notify, wohnung_frei)
            # Markiere sie als benachrichtigt und speichere den State
            for w in to_notify:
                state[w['typ']] = True
            save_state(state)
        else:
            print("Keine neuen offenen Wohnungen zum Benachrichtigen.")

except requests.exceptions.RequestException as e:
    print(f"Fehler beim Abrufen der Website: {e}")
except Exception as e:
    print(f"Ein Fehler ist aufgetreten: {e}")
