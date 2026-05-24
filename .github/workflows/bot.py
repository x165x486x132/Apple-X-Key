import discord
from discord.ext import commands
from discord import app_commands
import requests
import base64
import json
import uuid
import os
import asyncio

# --- CONFIGURATION ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GH_API_TOKEN = os.getenv("GH_API_TOKEN") # 👈 Changé ici !
REPO_NAME = "x165x486x132/Apple-X-Key"    # Ton repository
FILE_PATH = "hwid_db.json"               # Le fichier qui sert de base de données
ROLE_PREMIUM_ID = 1498644209840951468    # ID du rôle requis

# --- GESTION GITHUB API ---
def get_github_db():
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GH_API_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data['content']).decode('utf-8')
        return json.loads(content), data['sha']
    return {}, None

def update_github_db(json_data, sha):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GH_API_TOKEN}"}
    content_b64 = base64.b64encode(json.dumps(json_data, indent=4).encode('utf-8')).decode('utf-8')
    payload = {"message": "🤖 Update HWID Database", "content": content_b64}
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code in [200, 201]

# --- BOT SETUP ---
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

@bot.event
async def on_ready():
    print(f"✅ Bot connecté : {bot.user} - Commandes slash prêtes.")

# --- COMMANDE: COMMENT AVOIR SON HWID ---
@bot.tree.command(name="get_hwid", description="Obtiens le script pour copier ton HWID")
async def get_hwid(interaction: discord.Interaction):
    script = "```lua\nsetclipboard(game:GetService('RbxAnalyticsService'):GetClientId())\n```"
    await interaction.response.send_message(f"🛠️ **Comment obtenir ton HWID ?**\nExécute ce script dans ton exécuteur Roblox. Ton HWID sera copié dans ton presse-papier :\n{script}", ephemeral=True)

# --- COMMANDE: OBTENIR SA CLÉ ---
@bot.tree.command(name="key", description="Génère ta clé Premium avec ton HWID")
@app_commands.describe(hwid="Ton code HWID (Fais /get_hwid pour l'obtenir)")
async def generate_key(interaction: discord.Interaction, hwid: str):
    # Vérification du rôle Premium
    if not any(role.id == ROLE_PREMIUM_ID for role in interaction.user.roles):
        await interaction.response.send_message("❌ **Accès refusé.** Tu dois avoir le rôle Booster/Premium pour générer une clé.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True) # Fait patienter (car l'API GitHub prend qlq secondes)
    
    db, sha = get_github_db()
    user_id_str = str(interaction.user.id)

    # Récupérer l'ancienne clé ou créer une nouvelle
    if user_id_str in db:
        user_key = db[user_id_str]["key"]
        db[user_id_str]["hwid"] = hwid # Met à jour le HWID si nécessaire
    else:
        user_key = f"APPLEX-{uuid.uuid4().hex[:8].upper()}"
        db[user_id_str] = {"key": user_key, "hwid": hwid}

    # Sauvegarde sur GitHub
    success = update_github_db(db, sha)
    
    if success:
        script_to_copy = f'```lua\n_G.AppleKey = "{user_key}"\nloadstring(game:HttpGet("https://raw.githubusercontent.com/Tamachiru/AppleX/refs/heads/main/Game4"))()\n```'
        await interaction.followup.send(f"✅ **Base de données GitHub mise à jour.**\n\nVoici ton script d'accès personnel. Ton PC est désormais enregistré.\n{script_to_copy}\n\n*Note : Laisse passer 1 à 2 minutes pour que GitHub mette à jour le fichier avant de l'injecter dans Roblox.*")
    else:
        await interaction.followup.send("❌ Erreur lors de la sauvegarde sur GitHub. Vérifie que le secret GH_API_TOKEN est bien configuré et a les permissions 'Contents: Read & Write'.")

bot.run(DISCORD_TOKEN)
