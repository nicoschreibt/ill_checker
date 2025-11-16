import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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


def send_email(gefundene_wohnungen, wohnung_frei):
    """
    Sendet eine Email, wenn Wohnungen verfügbar sind.
    """
    # Email-Konfiguration
    sender_email = "nicolas.saameli@gmail.com"  # Ersetze mit deiner Email
    sender_password = "xxcm njqo fvfd ixjs"  # Ersetze mit App-Passwort
    receiver_email = "nicolas.saameli@protonmail.com"
    
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
        
        print(f"\n✓ Email erfolgreich an {receiver_email} gesendet!")
        
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
    
    # Email senden, wenn Wohnungen verfügbar sind
    if wohnung_frei != "geschlossen":
        send_email(gefundene_wohnungen, wohnung_frei)

except requests.exceptions.RequestException as e:
    print(f"Fehler beim Abrufen der Website: {e}")
except Exception as e:
    print(f"Ein Fehler ist aufgetreten: {e}")
