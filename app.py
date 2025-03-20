import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
from dotenv import load_dotenv
import os
import logging
import asyncio

# Logging einrichten
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('talk-bot')

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
        """Setup-Hook, der ausgeführt wird, wenn der Bot bereit ist"""
        logger.info(f'Angemeldet als {self.user}')
        try:
            synced = await self.tree.sync()
            logger.info(f"{len(synced)} Befehle synchronisiert")
        except Exception as e:
            logger.error(f"Fehler beim Synchronisieren der Befehle: {e}")
        
        # Hinweis für PyNaCl
        try:
            import nacl
            logger.info("PyNaCl ist installiert, Voice-Unterstützung ist aktiviert")
        except ImportError:
            logger.warning("PyNaCl ist nicht installiert. Bitte installiere es mit 'pip install PyNaCl' für Voice-Unterstützung")

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
            # Wir sind in einer DM, also müssen wir den Server finden
            guild = bot.get_guild(self.guild_id)
            if not guild:
                await interaction.response.send_message("❌ Server nicht gefunden. Bitte versuche es erneut.", ephemeral=True)
                return
                
            channel = guild.get_channel(self.channel_id)
            member = guild.get_member(self.user_id)
        else:
            # Wir sind in einem Server
            guild = interaction.guild
            channel = guild.get_channel(self.channel_id)
            member = interaction.user
        
        if entered_password == correct_password:
            # Passwort ist korrekt, Benutzer zur Liste der autorisierten Benutzer hinzufügen
            if self.channel_id not in bot.authorized_users:
                bot.authorized_users[self.channel_id] = []
            
            if self.user_id not in bot.authorized_users[self.channel_id]:
                bot.authorized_users[self.channel_id].append(self.user_id)
            
            # Bestätigungsnachricht senden
            await interaction.response.send_message(
                f"✅ Passwort korrekt! Du kannst jetzt dem Talk '{self.channel_name}' beitreten.", 
                ephemeral=True
            )
            
            logger.info(f"Benutzer {self.user_id} wurde für Talk-Kanal {self.channel_id} autorisiert")
        else:
            await interaction.response.send_message("❌ Falsches Passwort!", ephemeral=True)

# Benutzerdefinierte View für Passwort-Button
class PasswordButtonView(View):
    def __init__(self, channel_id, channel_name, guild_id, user_id):
        super().__init__(timeout=None)  # Kein Timeout für persistenten Button
        self.channel_id = channel_id
        self.channel_name = channel_name
        self.guild_id = guild_id
        self.user_id = user_id
        
        # Wir speichern die Informationen im custom_id
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
        super().__init__(timeout=None)  # Kein Timeout für persistenten Button
        self.channel_id = channel_id
        self.guild_id = guild_id
        
        # Wir speichern die Informationen im custom_id
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
    
    # Passwort-Button-Interaktion
    elif interaction.data.get("custom_id", "").startswith("enter_password_"):
        parts = interaction.data.get("custom_id").split("_")
        if len(parts) >= 5:
            channel_id = int(parts[2])
            guild_id = int(parts[3])
            user_id = int(parts[4])
            
            # Kanalname aus dem Speicher holen
            channel_name = bot.channel_names.get(channel_id, "Unbekannter Kanal")
            
            modal = PasswordModal(channel_id, channel_name, guild_id, user_id)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("❌ Ungültige Button-ID. Bitte versuche es erneut.", ephemeral=True)
    
    # Beitritts-Button-Interaktion
    elif interaction.data.get("custom_id", "").startswith("join_talk_"):
        parts = interaction.data.get("custom_id").split("_")
        if len(parts) >= 4:
            channel_id = int(parts[2])
            guild_id = int(parts[3])
            
            # Überprüfen, ob der Benutzer autorisiert ist
            if channel_id in bot.authorized_users and interaction.user.id in bot.authorized_users[channel_id]:
                # Benutzer ist autorisiert, also in den Kanal verschieben
                guild = bot.get_guild(guild_id)
                if guild:
                    channel = guild.get_channel(channel_id)
                    member = guild.get_member(interaction.user.id)
                    
                    if channel and member:
                        try:
                            await member.move_to(channel)
                            await interaction.response.send_message("✅ Du wurdest in den Talk verschoben.", ephemeral=True)
                        except Exception as e:
                            logger.error(f"Fehler beim Verschieben des Benutzers: {e}")
                            await interaction.response.send_message("❌ Fehler beim Verschieben in den Talk-Kanal.", ephemeral=True)
                    else:
                        if not channel:
                            await interaction.response.send_message("❌ Der Talk-Kanal existiert nicht mehr.", ephemeral=True)
                        else:
                            await interaction.response.send_message("❌ Fehler beim Finden deines Benutzers auf dem Server.", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ Server nicht gefunden.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Du bist nicht autorisiert, diesem Talk beizutreten.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Ungültige Button-ID. Bitte versuche es erneut.", ephemeral=True)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    """Voice-Status-Updates für Talk-Kanäle verarbeiten"""
    try:
        # Überprüfen, ob ein Benutzer einem Talk-Kanal beigetreten ist
        if after.channel and after.channel.id in bot.talk_creators:
            # Wenn der Benutzer bereits autorisiert ist oder der Ersteller des Talks ist, darf er bleiben
            if (after.channel.id in bot.authorized_users and member.id in bot.authorized_users[after.channel.id]) or \
               member.id == bot.talk_creators[after.channel.id]:
                if member.id == bot.talk_creators[after.channel.id]:
                    logger.info(f"Talk-Ersteller {member} hat seinen Talk-Kanal {after.channel.name} betreten")
                else:
                    logger.info(f"Autorisierter Benutzer {member} hat Talk-Kanal {after.channel.name} betreten")
                return
            
            # Wenn der Kanal passwortgeschützt ist und der Benutzer nicht autorisiert ist
            if after.channel.id in bot.talk_passwords:
                # Benutzer sofort aus dem Kanal entfernen
                try:
                    await member.move_to(None)
                    logger.info(f"Nicht autorisierter Benutzer {member.id} wurde aus Talk-Kanal {after.channel.id} entfernt")
                except Exception as e:
                    logger.error(f"Fehler beim Entfernen des Benutzers aus dem Kanal: {e}")
                
                # Kanalname aus dem Speicher holen oder vom Kanal selbst
                channel_name = bot.channel_names.get(after.channel.id, after.channel.name)
                
                # Passwort-Abfrage senden
                try:
                    embed = discord.Embed(
                        title="🔒 Passwortgeschützter Talk",
                        description=f"Der Talk-Kanal '{channel_name}' ist passwortgeschützt. Du musst zuerst das Passwort eingeben, bevor du beitreten kannst.",
                        color=discord.Color.orange()
                    )
                    
                    # Benutzerdefinierte View mit Passwort-Button erstellen
                    view = PasswordButtonView(after.channel.id, channel_name, member.guild.id, member.id)
                    
                    await member.send(embed=embed, view=view)
                except discord.Forbidden:
                    logger.warning(f"Konnte keine DM an {member} senden")

        # Überprüfen, ob ein Benutzer einen Talk-Kanal verlassen hat
        if before.channel and before.channel.id in bot.talk_creators:
            # Überprüfen, ob der Kanal leer ist
            if len(before.channel.members) == 0:
                # Warte 1 Minute, bevor der Kanal gelöscht wird
                await asyncio.sleep(60)
                
                # Überprüfen, ob der Kanal immer noch leer ist
                if len(before.channel.members) == 0:
                    try:
                        # Kanal löschen, wenn er leer ist
                        await before.channel.delete(reason="Talk-Kanal leer")
                        # Kanal aus den Dictionaries entfernen
                        del bot.talk_creators[before.channel.id]
                        if before.channel.id in bot.talk_passwords:
                            del bot.talk_passwords[before.channel.id]
                        if before.channel.id in bot.channel_names:
                            del bot.channel_names[before.channel.id]
                        if before.channel.id in bot.authorized_users:
                            del bot.authorized_users[before.channel.id]
                        logger.info(f"Leerer Talk-Kanal {before.channel.name} gelöscht")
                    except Exception as e:
                        logger.error(f"Fehler beim Löschen des Talk-Kanals: {e}")
            else:
                # Wenn der Ersteller den Kanal verlässt, aber andere Benutzer noch im Kanal sind
                if member.id == bot.talk_creators[before.channel.id]:
                    # Überprüfen, ob der Ersteller den Kanal verlassen hat
                    if len(before.channel.members) > 0:
                        # Der Kanal bleibt bestehen, solange andere Benutzer im Kanal sind
                        logger.info(f"Talk-Ersteller {member} hat den Kanal verlassen, aber der Kanal bleibt bestehen, da andere Benutzer noch im Kanal sind")
                    else:
                        # Wenn der Ersteller den Kanal verlässt und niemand mehr im Kanal ist, wird der Kanal nach 1 Minute gelöscht
                        await asyncio.sleep(60)
                        if len(before.channel.members) == 0:
                            try:
                                await before.channel.delete(reason="Talk-Kanal leer")
                                del bot.talk_creators[before.channel.id]
                                if before.channel.id in bot.talk_passwords:
                                    del bot.talk_passwords[before.channel.id]
                                if before.channel.id in bot.channel_names:
                                    del bot.channel_names[before.channel.id]
                                if before.channel.id in bot.authorized_users:
                                    del bot.authorized_users[before.channel.id]
                                logger.info(f"Leerer Talk-Kanal {before.channel.name} gelöscht")
                            except Exception as e:
                                logger.error(f"Fehler beim Löschen des Talk-Kanals: {e}")

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
    
    # Alle Talk-Kanäle in diesem Server finden
    talk_channels = []
    for channel_id, creator_id in bot.talk_creators.items():
        channel = guild.get_channel(channel_id)
        if channel:
            # Überprüfen, ob der Kanal passwortgeschützt ist
            is_password_protected = channel_id in bot.talk_passwords
            # Überprüfen, ob der Benutzer autorisiert ist
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
    
    # Embed mit allen Talks erstellen
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
    
    # Nachricht mit Embed senden
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
    
    # Talk-Kanal finden
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
    
    # Überprüfen, ob der Benutzer autorisiert ist
    is_authorized = (channel_id in bot.authorized_users and interaction.user.id in bot.authorized_users[channel_id]) or \
                    interaction.user.id == bot.talk_creators.get(channel_id)
    
    if is_authorized:
        # Benutzer ist autorisiert, also in den Kanal verschieben
        try:
            await interaction.user.move_to(channel)
            await interaction.response.send_message(f"✅ Du wurdest in den Talk '{channel.name}' verschoben.", ephemeral=True)
        except Exception as e:
            logger.error(f"Fehler beim Verschieben des Benutzers: {e}")
            await interaction.response.send_message("❌ Fehler beim Verschieben in den Talk-Kanal.", ephemeral=True)
    else:
        # Benutzer ist nicht autorisiert
        if channel_id in bot.talk_passwords:
            # Talk ist passwortgeschützt
            channel_name = bot.channel_names.get(channel_id, channel.name)
            
            embed = discord.Embed(
                title="🔒 Passwortgeschützter Talk",
                description=f"Der Talk-Kanal '{channel_name}' ist passwortgeschützt. Du musst zuerst das Passwort eingeben, bevor du beitreten kannst.",
                color=discord.Color.orange()
            )
            
            # Benutzerdefinierte View mit Passwort-Button erstellen
            view = PasswordButtonView(channel_id, channel_name, guild.id, interaction.user.id)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            # Talk ist nicht passwortgeschützt, aber der Benutzer ist trotzdem nicht autorisiert (sollte nicht vorkommen)
            await interaction.response.send_message("❌ Du bist nicht autorisiert, diesem Talk beizutreten.", ephemeral=True)

# Bot starten
if __name__ == "__main__":
    bot_token = os.getenv("DISCORD_BOT_TOKEN")
    if not bot_token:
        logger.critical("DISCORD_BOT_TOKEN nicht in den Umgebungsvariablen gefunden!")
        exit(1)
        
    # Hinweis für PyNaCl
    try:
        import nacl
    except ImportError:
        print("\n\n⚠️ WARNUNG: PyNaCl ist nicht installiert!")
        print("Voice-Unterstützung wird NICHT verfügbar sein.")
        print("Bitte installiere PyNaCl mit dem Befehl:")
        print("pip install PyNaCl\n\n")
    
    bot.run(bot_token)
