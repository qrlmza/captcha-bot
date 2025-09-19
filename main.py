import os
import random
import string
from dotenv import load_dotenv

import discord
from discord.ext import commands
from captcha.image import ImageCaptcha

# === Config ===
length = 6  # longueur captcha

# Charger .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
ROLE_ID = os.getenv("DISCORD_ROLE")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL")
GUILD_ID = os.getenv("DISCORD_GUILD")
VERIFIED_ROLE_ID = os.getenv("DISCORD_VERIFIED_ROLE")

ROLE_ID = int(ROLE_ID) if ROLE_ID else None
CHANNEL_ID = int(CHANNEL_ID) if CHANNEL_ID else None
GUILD_ID = int(GUILD_ID) if GUILD_ID else None
VERIFIED_ROLE_ID = int(VERIFIED_ROLE_ID) if VERIFIED_ROLE_ID else None

# === Bot ===
bot = commands.Bot(command_prefix="cp!", intents=discord.Intents.all())

# Créer le dossier captchas si inexistant
os.makedirs("captchas", exist_ok=True)

verify_channel = None
verify_role = None
verify_guild = None
verified_role = None


@bot.event
async def on_ready():
    global verify_channel, verify_role, verify_guild, verified_role
    print(f"{bot.user} is online.")

    if not GUILD_ID or not CHANNEL_ID or not ROLE_ID:
        print("[ERROR] Missing Discord IDs in .env file.")
        return

    verify_guild = bot.get_guild(GUILD_ID)
    verify_channel = bot.get_channel(CHANNEL_ID)
    verify_role = verify_guild.get_role(ROLE_ID)

    if VERIFIED_ROLE_ID:
        verified_role = verify_guild.get_role(VERIFIED_ROLE_ID)
        print(f"Loaded verified role from .env: {VERIFIED_ROLE_ID}")

    print("Loaded Discord IDs from .env!")


@bot.event
async def on_member_join(member: discord.Member):
    if member.guild.id != GUILD_ID:
        return

    # Donner rôle de vérification
    await member.add_roles(verify_role)

    # Générer captcha
    text = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
    file_name = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(20))
    image = ImageCaptcha(width=280, height=90)

    file_path = os.path.join("captchas", f"{file_name}.png")
    image.write(text, file_path)

    file = discord.File(file_path, filename=f"{file_name}.png")
    embed = discord.Embed(
        title="Verification",
        description=(
            "This server is using Captcha Verification\n"
            "to protect their server.\n\n"
            "Please type the letters shown below.\n\n"
            "**Note:** The captcha is **case-sensitive**.\n"
            "⏳ You have **30 seconds** to reply."
        ),
        color=0x9f4fd1
    )
    embed.set_image(url=f"attachment://{file_name}.png")
    msg = await verify_channel.send(content=member.mention, embed=embed, file=file)

    try:
        os.remove(file_path)
    except Exception:
        pass

    def check(m):
        return m.channel == verify_channel and m.author == member

    for attempt in range(3):
        try:
            reply = await bot.wait_for("message", check=check, timeout=30)
        except Exception:
            try:
                await member.kick(reason="Verification Timeout.")
            except Exception:
                pass
            return

        if reply.content.strip() == text:
            await member.remove_roles(verify_role)
            if verified_role:
                await member.add_roles(verified_role)
            try:
                await msg.delete()
                await reply.delete()
            except Exception:
                pass
            return
        else:
            if attempt < 2:
                await verify_channel.send(f"{member.mention} ❌ Invalid, {2 - attempt} attempts left.")

    try:
        await member.kick(reason="Too many captcha attempts.")
    except Exception:
        pass


@bot.command()
@commands.guild_only()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    """Créer automatiquement le rôle + channel de vérif"""
    msg = await ctx.send("Setting up guild...")
    role = await ctx.guild.create_role(name="Verifing")

    for channel in ctx.guild.channels:
        try:
            await channel.set_permissions(role, read_messages=False, send_messages=False, add_reactions=False)
        except Exception:
            pass

    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
        role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    channel = await ctx.guild.create_text_channel(name="verify-here", overwrites=overwrites, slowmode_delay=10)

    print(f"[SETUP] Add these values to your .env file:")
    print(f"DISCORD_ROLE={role.id}")
    print(f"DISCORD_CHANNEL={channel.id}")
    print(f"DISCORD_GUILD={ctx.guild.id}")

    await msg.edit(content="✅ Finished Setup! Check console for .env values.")


@bot.command()
@commands.guild_only()
@commands.has_permissions(administrator=True)
async def perms_setup(ctx):
    """Réapplique les permissions"""
    msg = await ctx.send("Rechecking perms...")
    for channel in ctx.guild.channels:
        try:
            await channel.set_permissions(verify_role, read_messages=False, send_messages=False, add_reactions=False)
        except Exception:
            pass

    await msg.edit(content="✅ Finished Setup!")


if not TOKEN:
    print("[ERROR] Discord token is missing or invalid. Please check your .env file and restart the bot.")
else:
    bot.run(TOKEN)
