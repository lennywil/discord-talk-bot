import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
from dotenv import load_dotenv
import os
import logging
import asyncio
import signal
import sys
from datetime import datetime
import shutil

# Logging einrichten
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('talk-bot')

# Live-Konsolenausgabe
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.handlers = [console_handler]  # Entfernt doppelte Handler

# Log-Ordner erstellen
log_dir = os.path.join(os.getcwd(), 'logs')
if not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir)
        logger.info(f"Log-Ordner erstellt: {log_dir}")
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Log-Ordners: {e}")

# Log-Datei mit Startzeit initialisieren
start_time = datetime.now()
start_time_str = start_time.strftime('%Y-%m-%d, %H-%M-%S')
log_file_name = f"{start_time_str} - .log"
log_file_path = os.path.join(log_dir, log_file_name)

file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Funktion zum Umbenennen der Log-Datei beim Beenden
def rename_log_file(signal_number=None, frame=None):
    try:
        file_handler.close()
        logger.handlers.remove(file_handler)
        end_time = datetime.now()
        end_time_str = end_time.strftime('%H-%M-%S')
        new_log_file_name = f"{start_time_str} - {end_time_str}.log"
        new_log_file_path = os.path.join(log_dir, new_log_file_name)
        if os.path.exists(log_file_path):
            shutil.move(log_file_path, new_log_file_path)
            logger.info(f"Log-Datei umbenannt zu: {new_log_file_name}")
    except Exception as e:
        logger.error(f"Fehler beim Umbenennen der Log-Datei: {e}")
    finally:
        if signal_number == signal.SIGINT:
            print("stopt")
        logger.info("Bot ordnungsgemäß beendet")
        sys.exit(0)

# Signal-Handler für SIGINT und SIGTERM
signal.signal(signal.SIGINT, rename_log_file)
signal.signal(signal.SIGTERM, rename_log_file)

# Asynchrone Funktion zum periodischen Umbenennen der Log-Datei
async def update_log_file_name():
    global log_file_path, file_handler
    while True:
        try:
            # Alten FileHandler schließen und entfernen
            file_handler.close()
            logger.handlers.remove(file_handler)
            
            # Neue Zeit für Dateinamen
            current_time = datetime.now()
            current_time_str = current_time.strftime('%H-%M-%S')
            new_log_file_name = f"{start_time_str} - {current_time_str}.log"
            new_log_file_path = os.path.join(log_dir, new_log_file_name)
            
            # Alte Log-Datei umbenennen
            if os.path.exists(log_file_path):
                shutil.move(log_file_path, new_log_file_path)
            
            # Neuen FileHandler erstellen
            log_file_path = new_log_file_path
            file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(file_handler)
            
            # Eine Sekunde warten
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Fehler beim periodischen Umbenennen der Log-Datei: {e}")
            await asyncio.sleep(1)  # Fortfahren, auch wenn ein Fehler auftritt

# Umgebungsvariablen laden
load_dotenv()

# Bot-Konfiguration
class TalkBot(commands.Bot):
    def __init__(self):
        # Intents konfigurieren
        intents = discord.Intents.default()
        intents.message_content = True  # Für das Lesen von Nachrichteninhalten
        intents.members = True          # Für den Zugriff auf Servermitglieder
        intents.presences = True        # Für den Zugriff auf Benutzerstatus
        intents.voice_states = True     # Für die Überwachung von Voice-Zuständen
        
        super().__init__(command_prefix="!", intents=intents)
        
        # Speicher für Talk-Einstellungen und Ersteller
        self.talk_settings = {}  # {guild_id: {"category": category_obj, "channel": channel_obj}}
        self.talk_creators = {}  # {channel_id: creator_user_id}
        self.talk_passwords = {}  # {channel_id: password}
        # Speichern der ursprünglichen Kanalnamen für Fehlerbehebung
        self.channel_names = {}  # {channel_id: channel_name}
        # Speichern der autorisierten Benutzer für jeden Kanal
        self.authorized_users = {}  # {channel_id: [user_id1, user_id2, ...]}
    
    async def setup_hook(self):
        """Setup-Hook, der ausgeführt wird, wenn der Bot initialisiert ist"""
        print("done", flush=True)  # Frühe Ausgabe für Pelican Panel
        logger.info(f'Angemeldet als {self.user}')
        try:
            synced = await self.tree.sync()
            logger.info(f"{len(synced)} Befehle synchronisiert")
        except Exception as e:
            logger.error(f"Fehler beim Synchronisieren der Befehle: {e}")
        
        # Hintergrundtask zum Umbenennen der Log-Datei starten
        self.loop.create_task(update_log_file_name())
        
        # Hinweis für PyNaCl
        try:
            import nacl
            logger.info("PyNaCl ist installiert, Voice-Unterstützung ist aktiviert")
        except ImportError:
            logger.warning("PyNaCl ist nicht installiert. Bitte installiere es mit 'pip install PyNaCl' für Voice-Unterstützung")
    
    async def on_ready(self):
        """Wird aufgerufen, wenn der Bot vollständig bereit ist"""
        try:
            activity = discord.CustomActivity(
                name="allosmp Talk Bot | https://allosmp.de/discord_talk_bot"
            )
            await self.change_presence(activity=activity)
            logger.info("Bot-Beschreibung gesetzt: allosmp Talk Bot | https://allosmp.de/discord_talk_bot")
            print("done", flush=True)  # Zweite Ausgabe für Robustheit
        except Exception as e:
            logger.error(f"Fehler beim Setzen der Bot-Beschreibung: {e}")

# UI-Komponenten
class TalkCreationModal(Modal):
    def __init__(self):
        super().__init__(title="Talk-Nachricht erstellen")
        
        self.channel = TextInput(
            label="Kanalname", 
            placeholder="Gib den Namen des Kanals ein, in dem die Nachricht gepostet werden soll",
            required=True
        )
        self.message = TextInput(
            label="Nachrichteninhalt", 
            placeholder="Gib den Inhalt der Nachricht ein", 
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.category = TextInput(
            label="Kategoriename", 
            placeholder="Gib den Namen der Kategorie ein, in der Talks erstellt werden sollen",
            required=True
        )
        
        self.add_item(self.channel)
        self.add_item(self.message)
        self.add_item(self.category)

    async def on_submit(self, interaction: discord.Interaction):
        channel = discord.utils.get(interaction.guild.text_channels, name=self.channel.value)
        category = discord.utils.get(interaction.guild.categories, name=self.category.value)

        if not channel:
            await interaction.response.send_message("❌ Kanal nicht gefunden!", ephemeral=True)
            return
            
        if not category:
            await interaction.response.send_message("❌ Kategorie nicht gefunden!", ephemeral=True)
            return

        # Einstellungen für diesen Server speichern
        bot.talk_settings[interaction.guild.id] = {"category": category, "channel": channel}

        # Talk-Erstellungsnachricht erstellen und senden
        embed = discord.Embed(
            title="📣 Erstelle einen Talk-Kanal", 
            description=self.message.value,
            color=discord.Color.blue()
        )
        
        # Button-View erstellen
        view = View(timeout=None)  # Kein Timeout für persistenten Button
        view.add_item(Button(
            label="Talk erstellen", 
            style=discord.ButtonStyle.primary, 
            custom_id="create_talk",
            emoji="🎙️"
        ))

        await channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Talk-Erstellungsnachricht erfolgreich eingerichtet!", ephemeral=True)

class CreateTalkModal(Modal):
    def __init__(self):
        super().__init__(title="Erstelle deinen Talk")
        
        self.talk_name = TextInput(
            label="Talk-Name", 
            placeholder="Gib den Namen deines Talks ein",
            required=True,
            max_length=32
        )
        
        self.password_required = TextInput(
            label="Passwort erforderlich?", 
            placeholder="Ja oder Nein",
            required=True,
            max_length=3
        )
        
        self.password = TextInput(
            label="Passwort (falls erforderlich)", 
            placeholder="Leer lassen, wenn kein Passwort benötigt wird",
            required=False,
            max_length=20
        )
        
        self.add_item(self.talk_name)
        self.add_item(self.password_required)
        self.add_item(self.password)
    
    async def on_submit(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        
        if guild_id not in bot.talk_settings:
            await interaction.response.send_message("❌ Das Talk-System ist in diesem Server nicht eingerichtet!", ephemeral=True)
            return
            
        category = bot.talk_settings[guild_id]["category"]
        
        # Überprüfen, ob ein Passwort erforderlich ist
        password_required = self.password_required.value.lower() in ["ja", "yes", "j", "y"]
        password = self.password.value if password_required else None
        
        if password_required and not password:
            await interaction.response.send_message("❌ Du hast angegeben, dass ein Passwort erforderlich ist, aber keines eingegeben!", ephemeral=True)
            return
        
        try:
            # Voice-Kanal erstellen
            prefix = "🔒" if password_required else "🎙️"
            new_channel = await interaction.guild.create_voice_channel(
                name=f"{prefix} {self.talk_name.value}", 
                category=category
            )
            
            # Ersteller des Talks speichern
            bot.talk_creators[new_channel.id] = interaction.user.id
            
            # Passwort speichern, falls erforderlich
            if password_required:
                bot.talk_passwords[new_channel.id] = password
                
            # Kanalname für spätere Referenz speichern
            bot.channel_names[new_channel.id] = new_channel.name
            
            # Ersteller zur Liste der autorisierten Benutzer hinzufügen
            bot.authorized_users[new_channel.id] = [interaction.user.id]
            
            password_info = "mit Passwortschutz" if password_required else "ohne Passwortschutz"
            await interaction.response.send_message(
                f"✅ Dein Talk wurde in {new_channel.mention} erstellt ({password_info})!", 
                ephemeral=True
            )
            
            logger.info(f"Talk-Kanal '{new_channel.name}' erstellt von {interaction.user}")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich habe keine Berechtigung, Voice-Kanäle zu erstellen!", 
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Talk-Kanals: {e}")
            await interaction.response.send_message(
                "❌ Beim Erstellen deines Talk-Kanals ist ein Fehler aufgetreten.", 
                ephemeral=True
            )

class PasswordModal(Modal):
    def __init__(self, channel_id, channel_name, guild_id, user_id):
        super().__init__(title="Passwort eingeben")
        self.channel_id = channel_id
        self.channel_name = channel_name
        self.guild_id = guild_id
        self.user_id = user_id
        
        self.password = TextInput(
            label="Passwort", 
            placeholder="Gib das Passwort für diesen Talk ein",
            required=True
        )
        
        self.add_item(self.password)
    
    async def on_submit(self, interaction: discord.Interaction):
        entered_password = self.password.value
        correct_password = bot.talk_passwords.get(self.channel_id)
        
        # Überprüfen, ob wir in einer DM sind
        if interaction.guild is None:
            guild = bot.get_guild(self.guild_id)
            if not guild:
                await interaction.response.send_message("❌ Server nicht gefunden. Bitte versuche es erneut.", ephemeral=True)
                return
            channel = guild.get_channel(self.channel_id)
            member = guild.get_member(self.user_id)
        else:
            guild = interaction.guild
            channel = guild.get_channel(self.channel_id)
            member = interaction.user
        
        if not channel or not member:
            await interaction.response.send_message("❌ Kanal oder Benutzer nicht gefunden.", ephemeral=True)
            return
        
        if entered_password == correct_password:
            # Passwort ist korrekt, Benutzer autorisieren
            if self.channel_id not in bot.authorized_users:
                bot.authorized_users[self.channel_id] = []
            if self.user_id not in bot.authorized_users[self.channel_id]:
                bot.authorized_users[self.channel_id].append(self.user_id)
            
            logger.info(f"Benutzer {self.user_id} wurde für Talk-Kanal {self.channel_id} autorisiert")
            
            # Überprüfen, ob der Benutzer mit einem Voice-Channel verbunden ist
            if member.voice and member.voice.channel:
                try:
                    await member.move_to(channel)
                    await interaction.response.send_message(
                        f"✅ Passwort korrekt! Du wurdest in den Talk '{self.channel_name}' verschoben.", 
                        ephemeral=True
                    )
                    logger.info(f"Benutzer {member.id} wurde in Talk-Kanal {self.channel_id} verschoben")
                except Exception as e:
                    logger.error(f"Fehler beim Verschieben des Benutzers in den Kanal: {e}")
                    await interaction.response.send_message(
                        f"✅ Passwort korrekt! Bitte tritt dem Talk '{self.channel_name}' manuell bei.", 
                        ephemeral=True
                    )
            else:
                await interaction.response.send_message(
                    f"✅ Passwort korrekt! Bitte tritt dem Talk '{self.channel_name}' manuell bei, da du derzeit nicht in einem Voice-Channel bist.", 
                    ephemeral=True
                )
        else:
            await interaction.response.send_message("❌ Falsches Passwort!", ephemeral=True)
            logger.info(f"Benutzer {self.user_id} hat ein falsches Passwort für Talk-Kanal {self.channel_id} eingegeben")

# Benutzerdefinierte View für Passwort-Button
class PasswordButtonView(View):
    def __init__(self, channel_id, channel_name, guild_id, user_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.channel_name = channel_name
        self.guild_id = guild_id
        self.user_id = user_id
        
        custom_id = f"enter_password_{channel_id}_{guild_id}_{user_id}"
        self.add_item(Button(
            label="Passwort eingeben", 
            style=discord.ButtonStyle.primary, 
            custom_id=custom_id,
            emoji="🔑"
        ))

# Benutzerdefinierte View für den Beitritts-Button
class JoinTalkButtonView(View):
    def __init__(self, channel_id, guild_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.guild_id = guild_id
        
        custom_id = f"join_talk_{channel_id}_{guild_id}"
        self.add_item(Button(
            label="Talk beitreten", 
            style=discord.ButtonStyle.success, 
            custom_id=custom_id,
            emoji="🎙️"
        ))

# Bot-Instanz erstellen
bot = TalkBot()

# Befehle
@bot.tree.command(
    name="talk_system_einrichten", 
    description="Richte das Talk-Erstellungssystem für deinen Server ein"
)
@app_commands.default_permissions(administrator=True)
async def setup_talk_system(interaction: discord.Interaction):
    """Befehl zum Einrichten des Talk-Erstellungssystems"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Du benötigst Administratorrechte, um diesen Befehl zu verwenden!", ephemeral=True)
        return

    modal = TalkCreationModal()
    await interaction.response.send_modal(modal)

# Event-Handler
@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Button-Interaktionen verarbeiten"""
    if not interaction.type == discord.InteractionType.component:
        return
        
    if interaction.data.get("custom_id") == "create_talk":
        modal = CreateTalkModal()
        await interaction.response.send_modal(modal)
    
    elif interaction.data.get("custom_id", "").startswith("enter_password_"):
        parts = interaction.data.get("custom_id").split("_")
        if len(parts) >= 5:
            channel_id = int(parts[2])
            guild_id = int(parts[3])
            user_id = int(parts[4])
            channel_name = bot.channel_names.get(channel_id, "Unbekannter Kanal")
            modal = PasswordModal(channel_id, channel_name, guild_id, user_id)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("❌ Ungültige Button-ID. Bitte versuche es erneut.", ephemeral=True)
    
    elif interaction.data.get("custom_id", "").startswith("join_talk_"):
        parts = interaction.data.get("custom_id").split("_")
        if len(parts) >= 4:
            channel_id = int(parts[2])
            guild_id = int(parts[3])
            
            if channel_id in bot.authorized_users and interaction.user.id in bot.authorized_users[channel_id]:
                guild = bot.get_guild(guild_id)
                if guild:
                    channel = guild.get_channel(channel_id)
                    member = guild.get_member(interaction.user.id)
                    
                    if channel and member and member.voice and member.voice.channel:
                        try:
                            await member.move_to(channel)
                            await interaction.response.send_message("✅ Du wurdest in den Talk verschoben.", ephemeral=True)
                            logger.info(f"Benutzer {member.id} wurde in Talk-Kanal {channel_id} verschoben")
                        except Exception as e:
                            logger.error(f"Fehler beim Verschieben des Benutzers: {e}")
                            await interaction.response.send_message("❌ Fehler beim Verschieben in den Talk-Kanal.", ephemeral=True)
                    else:
                        await interaction.response.send_message("❌ Du musst in einem Voice-Channel sein, um verschoben zu werden.", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ Server nicht gefunden.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Du bist nicht autorisiert, diesem Talk beizutreten.", ephemeral=True)
                logger.info(f"Benutzer {interaction.user.id} nicht autorisiert für Talk-Kanal {channel_id}")
        else:
            await interaction.response.send_message("❌ Ungültige Button-ID. Bitte versuche es erneut.", ephemeral=True)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    """Voice-Status-Updates für Talk-Kanäle verarbeiten"""
    logger.debug(f"on_voice_state_update: Member: {member}, Before: {before.channel}, After: {after.channel}")
    try:
        # Überprüfen, ob ein Benutzer einem Talk-Kanal beigetreten ist
        if after.channel is not None and after.channel.id in bot.talk_creators:
            # Wenn der Benutzer autorisiert ist oder der Ersteller, darf er bleiben
            if (after.channel.id in bot.authorized_users and member.id in bot.authorized_users[after.channel.id]) or \
               member.id == bot.talk_creators.get(after.channel.id):
                if member.id == bot.talk_creators.get(after.channel.id):
                    logger.info(f"Talk-Ersteller {member} hat seinen Talk-Kanal {after.channel.name} betreten")
                else:
                    logger.info(f"Autorisierter Benutzer {member} hat Talk-Kanal {after.channel.name} betreten")
                return

            # Wenn der Kanal passwortgeschützt ist und der Benutzer nicht autorisiert
            if after.channel.id in bot.talk_passwords:
                channel_name = bot.channel_names.get(after.channel.id, after.channel.name)
                
                # Passwort-Abfrage senden
                try:
                    embed = discord.Embed(
                        title="🔒 Passwortgeschützter Talk",
                        description=f"Der Talk-Kanal '{channel_name}' ist passwortgeschützt. Du musst zuerst das Passwort eingeben, bevor du beitreten kannst.",
                        color=discord.Color.orange()
                    )
                    view = PasswordButtonView(after.channel.id, channel_name, member.guild.id, member.id)
                    await member.send(embed=embed, view=view)
                    logger.info(f"Passwort-Abfrage an {member} für Kanal {channel_name} gesendet")
                except discord.Forbidden:
                    logger.warning(f"Konnte keine DM an {member} senden")
                
                # Benutzer aus dem Kanal entfernen, wenn er noch verbunden ist
                if member.voice and member.voice.channel:
                    try:
                        await member.move_to(None)
                        logger.info(f"Nicht autorisierter Benutzer {member.id} wurde aus Talk-Kanal {after.channel.id} entfernt")
                    except Exception as e:
                        logger.error(f"Fehler beim Entfernen des Benutzers aus dem Kanal: {e}")

        # Überprüfen, ob ein Benutzer einen Talk-Kanal verlassen hat
        if before.channel is not None and before.channel.id in bot.talk_creators:
            if len(before.channel.members) == 0:
                await asyncio.sleep(60)
                channel = bot.get_channel(before.channel.id)
                if channel and len(channel.members) == 0:
                    try:
                        await channel.delete(reason="Talk-Kanal leer")
                        bot.talk_creators.pop(before.channel.id, None)
                        bot.talk_passwords.pop(before.channel.id, None)
                        bot.channel_names.pop(before.channel.id, None)
                        bot.authorized_users.pop(before.channel.id, None)
                        logger.info(f"Leerer Talk-Kanal {before.channel.name} gelöscht")
                    except Exception as e:
                        logger.error(f"Fehler beim Löschen des Talk-Kanals: {e}")
            else:
                if member.id == bot.talk_creators.get(before.channel.id):
                    logger.info(f"Talk-Ersteller {member} hat den Kanal verlassen, aber der Kanal bleibt bestehen, da andere Benutzer noch im Kanal sind")

    except Exception as e:
        logger.error(f"Fehler in on_voice_state_update: {e}")

# Befehl zum Anzeigen aller verfügbaren Talks
@bot.tree.command(
    name="talks_anzeigen",
    description="Zeigt alle verfügbaren Talks an"
)
async def list_talks(interaction: discord.Interaction):
    """Befehl zum Anzeigen aller verfügbaren Talks"""
    guild = interaction.guild
    
    talk_channels = []
    for channel_id, creator_id in bot.talk_creators.items():
        channel = guild.get_channel(channel_id)
        if channel:
            is_password_protected = channel_id in bot.talk_passwords
            is_authorized = (channel_id in bot.authorized_users and interaction.user.id in bot.authorized_users[channel_id]) or \
                            interaction.user.id == creator_id
            talk_channels.append({
                "channel": channel,
                "password_protected": is_password_protected,
                "authorized": is_authorized
            })
    
    if not talk_channels:
        await interaction.response.send_message("Es sind derzeit keine Talks verfügbar.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="📣 Verfügbare Talks",
        description="Hier sind alle verfügbaren Talks auf diesem Server:",
        color=discord.Color.blue()
    )
    
    for talk in talk_channels:
        channel = talk["channel"]
        status = "🔒 Passwortgeschützt" if talk["password_protected"] else "🔓 Offen"
        access = "✅ Zugriff erlaubt" if talk["authorized"] else "❌ Zugriff verweigert"
        embed.add_field(
            name=channel.name,
            value=f"{status}\n{access}\nMitglieder: {len(channel.members)}",
            inline=True
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Befehl zum Beitreten zu einem Talk
@bot.tree.command(
    name="talk_beitreten",
    description="Tritt einem Talk bei"
)
@app_commands.describe(
    talk_name="Der Name des Talks, dem du beitreten möchtest"
)
async def join_talk(interaction: discord.Interaction, talk_name: str):
    """Befehl zum Beitreten zu einem Talk"""
    guild = interaction.guild
    
    channel = None
    channel_id = None
    for ch in guild.voice_channels:
        if talk_name.lower() in ch.name.lower() and ch.id in bot.talk_creators:
            channel = ch
            channel_id = ch.id
            break
    
    if not channel:
        await interaction.response.send_message(f"❌ Kein Talk mit dem Namen '{talk_name}' gefunden.", ephemeral=True)
        return
    
    is_authorized = (channel_id in bot.authorized_users and interaction.user.id in bot.authorized_users[channel_id]) or \
                    interaction.user.id == bot.talk_creators.get(channel_id)
    
    if is_authorized:
        if interaction.user.voice and interaction.user.voice.channel:
            try:
                await interaction.user.move_to(channel)
                await interaction.response.send_message(f"✅ Du wurdest in den Talk '{channel.name}' verschoben.", ephemeral=True)
                logger.info(f"Benutzer {interaction.user.id} wurde in Talk-Kanal {channel_id} verschoben")
            except Exception as e:
                logger.error(f"Fehler beim Verschieben des Benutzers: {e}")
                await interaction.response.send_message("❌ Fehler beim Verschieben in den Talk-Kanal.", ephemeral=True)
        else:
            await interaction.response.send_message(f"✅ Du bist autorisiert! Bitte tritt dem Talk '{channel.name}' manuell bei, da du nicht in einem Voice-Channel bist.", ephemeral=True)
    else:
        if channel_id in bot.talk_passwords:
            channel_name = bot.channel_names.get(channel_id, channel.name)
            embed = discord.Embed(
                title="🔒 Passwortgeschützter Talk",
                description=f"Der Talk-Kanal '{channel_name}' ist passwortgeschützt. Du musst zuerst das Passwort eingeben, bevor du beitreten kannst.",
                color=discord.Color.orange()
            )
            view = PasswordButtonView(channel_id, channel_name, guild.id, interaction.user.id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            logger.info(f"Passwort-Abfrage an {interaction.user} für Kanal {channel_name} gesendet")
        else:
            await interaction.response.send_message("❌ Du bist nicht autorisiert, diesem Talk beizutreten.", ephemeral=True)
            logger.info(f"Benutzer {interaction.user.id} nicht autorisiert für Talk-Kanal {channel_id}")

# Bot starten
if __name__ == "__main__":
    bot_token = os.getenv("DISCORD_BOT_TOKEN")
    if not bot_token:
        print("ERROR: DISCORD_BOT_TOKEN nicht gefunden!", flush=True)
        logger.critical("DISCORD_BOT_TOKEN nicht in den Umgebungsvariablen gefunden!")
        exit(1)
        
    try:
        import nacl
    except ImportError:
        print("\n\n⚠️ WARNUNG: PyNaCl ist nicht installiert!", flush=True)
        print("Voice-Unterstützung wird NICHT verfügbar sein.", flush=True)
        print("Bitte installiere PyNaCl mit dem Befehl:", flush=True)
        print("pip install PyNaCl\n\n", flush=True)
    
    print("Starting bot...", flush=True)
    try:
        bot.run(bot_token)
    except Exception as e:
        print(f"ERROR: Bot konnte nicht gestartet werden: {e}", flush=True)
        logger.error(f"Fehler beim Ausführen des Bots: {e}")
        rename_log_file()
