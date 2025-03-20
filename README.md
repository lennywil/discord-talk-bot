# Discord Talk Bot

Der **Discord Talk Bot** ist ein vielseitiger Bot, der es Benutzern ermöglicht, temporäre Voice-Kanäle (Talks) zu erstellen, zu verwalten und diesen beizutreten. Der Bot bietet Funktionen wie Passwortschutz, automatische Löschung leerer Kanäle und eine benutzerfreundliche Oberfläche zur Verwaltung der Talks.

## Funktionen

- **Erstellung von Talk-Kanälen**: Benutzer können temporäre Voice-Kanäle erstellen, die automatisch gelöscht werden, wenn sie leer sind.
- **Passwortschutz**: Talks können mit einem Passwort geschützt werden, um den Zugriff auf autorisierte Benutzer zu beschränken.
- **Benutzerfreundliche Oberfläche**: Der Bot verwendet modale Dialoge und Buttons, um die Interaktion zu vereinfachen.
- **Automatische Kanalverwaltung**: Leere Talk-Kanäle werden automatisch nach einer gewissen Zeit gelöscht.
- **Beitrittsberechtigungen**: Nur autorisierte Benutzer können passwortgeschützten Talks beitreten.

## Voraussetzungen

- **Python 3.8 oder höher**
- **Discord.py Bibliothek**: `pip install discord.py`
- **PyNaCl** (für Voice-Unterstützung): `pip install PyNaCl`
- **Dotenv** (für Umgebungsvariablen): `pip install python-dotenv`

## Installation

1. **Klonen des Repositorys**:
   ```bash
   git clone https://github.com/dein-repository/discord-talk-bot.git
   cd discord-talk-bot
   ```

2. **Umgebungsvariablen einrichten**:
   Erstelle eine `.env`-Datei im Stammverzeichnis des Projekts und füge deinen Discord-Bot-Token hinzu:
   ```env
   DISCORD_BOT_TOKEN=dein_bot_token
   ```

3. **Abhängigkeiten installieren**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Bot starten**:
   ```bash
   python bot.py
   ```

## Verwendung

### Talk-System einrichten

1. Verwende den Befehl `/talk_system_einrichten`, um das Talk-System auf deinem Server einzurichten.
2. Gib den Kanalnamen, die Nachricht und den Kategorienamen ein, in dem die Talks erstellt werden sollen.

### Talk erstellen

1. Klicke auf den Button "Talk erstellen", der in dem von dir angegebenen Kanal angezeigt wird.
2. Gib den Namen des Talks ein und lege fest, ob ein Passwort erforderlich ist.
3. Der Talk-Kanal wird in der angegebenen Kategorie erstellt.

### Talk beitreten

1. Verwende den Befehl `/talks_anzeigen`, um alle verfügbaren Talks anzuzeigen.
2. Verwende den Befehl `/talk_beitreten`, um einem Talk beizutreten. Wenn der Talk passwortgeschützt ist, wirst du aufgefordert, das Passwort einzugeben.

### Passwortschutz

- Wenn ein Talk passwortgeschützt ist, müssen Benutzer das Passwort eingeben, bevor sie dem Talk beitreten können.
- Das Passwort wird in einer DM (Direktnachricht) eingegeben, um die Sicherheit zu gewährleisten.

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Weitere Informationen findest du in der [LICENSE](LICENSE)-Datei.

## Beitrag

Falls du einen Beitrag leisten möchtest, öffne bitte ein Issue oder einen Pull Request. Wir freuen uns über jede Art von Feedback und Verbesserungsvorschlägen.

## Kontakt

Bei Fragen oder Problemen kannst du dich gerne an uns wenden:

- **E-Mail**: mail@lennardwilmer.eu
- **Discord-Server**: [Beitreten](https://discord.allosmp.de)

---

Viel Spaß mit dem Discord Talk Bot! 🎙️
