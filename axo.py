import os
import random
from discord.ext import commands, tasks
import discord
from dotenv import load_dotenv
import sqlite3
import datetime
import aiohttp
import psutil
import subprocess
import platform
from PIL import Image, ImageOps
import io
import asyncio
from discord import app_commands

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
intents.messages = True
intents.guilds = True

client = commands.Bot(command_prefix=".", intents=intents)

conn = sqlite3.connect('ranks.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS ranks
             (user_id INTEGER PRIMARY KEY, points INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS currency
             (user_id INTEGER PRIMARY KEY, balance INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS daily_rewards
             (user_id INTEGER PRIMARY KEY, last_claimed TEXT)''')
conn.commit()

start_time = datetime.datetime.utcnow()
latency_values = []
errors = []  # Global list to store errors

@client.event
async def on_ready():
    print(f'{client.user.name} has connected to Discord!')
    update_latency.start()

client.remove_command('help')

@client.command()
async def help(ctx):
    commands = {
        ".help": "Shows this message",
        ".ping": "Checks the bot's ping",
        ".roll": "Rolls a dice",
        ".8ball": "The magic 8ball",
        ".avatar": "Show the avatar of a user",
        ".userinfo": "Shows the user info",
        ".leaderboard": "Shows the leaderboard",
        ".poll": "Make a poll",
        ".meme": "Shows a meme",
        ".coinflip": "Flips a coin",
        ".statistics": "Shows system statistics",
        ".cat": "Shows a random cat image",
        ".dog": "Shows a random dog image",
        ".joke": "Tells a random joke",
        ".quote": "Shares a random quote",
        ".fact": "Shares a random fact",
        ".advice": "Gives random advice",
        ".compliment": "Gives a compliment",
        ".insult": "Gives a lighthearted insult",
        ".rps": "Play rock-paper-scissors",
        ".say": "Repeats after you",
        ".reverse": "Reverses your message",
        ".choose": "Helps you make a choice",
        ".invert": "Inverts someone's profile picture",
        ".balance": "Shows your balance",
        ".deposit": "Deposits money into your account",
        ".withdraw": "Withdraws money from your account",
        ".find": "Finds random money",
        ".gamble": "Gambles an amount of money",
        ".rob": "Rob another user",
        ".give": "Give money to another user",
        ".daily": "Claim your daily reward",
        ".work": "Work to earn money",
        ".crime": "Commit a crime for money",
        ".quiz": "Just a quiz"
    }
    help_message = "\n".join([
        f"{command}: {description}"
        for command, description in commands.items()
    ])
    await ctx.send(f"Available commands:\n{help_message}")

def get_balance(user_id):
    c.execute('SELECT balance FROM currency WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    if result:
        return result[0]
    else:
        c.execute('INSERT INTO currency (user_id, balance) VALUES (?, ?)', (user_id, 0))
        conn.commit()
        return 0

def update_balance(user_id, amount):
    c.execute('SELECT balance FROM currency WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    if result:
        new_balance = result[0] + amount
        c.execute('UPDATE currency SET balance = ? WHERE user_id = ?', (new_balance, user_id))
    else:
        c.execute('INSERT INTO currency (user_id, balance) VALUES (?, ?)', (user_id, amount))
    conn.commit()

@client.command(aliases=['bal'])
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    balance = get_balance(member.id)
    await ctx.send(f"{member.name}, your balance is {balance} coins.")

@client.command()
async def deposit(ctx, amount: int):
    user_id = ctx.author.id
    balance = get_balance(user_id)
    if amount <= 0:
        await ctx.send("Amount must be positive!")
        return

    # Simulate an external balance check
    external_balance = balance  # This is a placeholder. Replace with actual external balance check.

    if amount > external_balance:
        await ctx.send("You do not have enough funds to deposit that amount!")
        return

    new_balance = balance + amount
    update_balance(user_id, amount)
    await ctx.send(f"You deposited {amount} coins. New balance is {new_balance} coins.")

@client.command()
async def withdraw(ctx, amount: int):
    user_id = ctx.author.id
    balance = get_balance(user_id)
    if amount <= 0:
        await ctx.send("Amount must be positive!")
        return
    
    external_balance = balance

    if amount > external_balance:
        await ctx.send("Insufficient balance!")
        return
    new_balance = balance - amount
    update_balance(user_id, -amount)
    await ctx.send(f"You withdrew {amount} coins. New balance is {new_balance} coins.")

@client.event
async def on_ready():
    await client.tree.sync()
    print(f'Logged in as {client.user}')

@client.tree.command(name="ping", description="Check the bot's latency")
async def ping(interaction: discord.Interaction):
    latency = round(client.latency * 1000)
    await interaction.response.send_message(f'Pong! Latency is {latency}ms.')

@client.command()
async def leaderboard(ctx, limit: int = 10):
    c.execute('SELECT user_id, balance FROM currency ORDER BY balance DESC LIMIT ?', (limit,))
    top_users = c.fetchall()
    
    leaderboard_embed = discord.Embed(
        title=f"Top {limit} Richest Users",
        color=discord.Color.gold()
    )
    
    for index, (user_id, balance) in enumerate(top_users, start=1):
        user = client.get_user(user_id)
        if user:
            leaderboard_embed.add_field(
                name=f"{index}. {user.name}",
                value=f"Balance: {balance} coins",
                inline=False
            )
    
    await ctx.send(embed=leaderboard_embed)


@client.command()
async def find(ctx):
    user_id = ctx.author.id
    if random.randint(1, 10) > 2:  # 80% chance to find money
        found_amount = random.randint(50, 200)
        update_balance(user_id, found_amount)
        await ctx.send(f"You found {found_amount} coins! New balance is {get_balance(user_id)} coins.")
    else:  # 20% chance to get robbed
        lost_amount = random.randint(20, 100)
        update_balance(user_id, -lost_amount)
        await ctx.send(f"You got robbed and lost {lost_amount} coins! New balance is {get_balance(user_id)} coins.")

@client.command()
async def gamble(ctx, amount: int):
    user_id = ctx.author.id
    balance = get_balance(user_id)
    if amount <= 0:
        await ctx.send("Amount must be positive!")
        return
    if amount > balance:
        await ctx.send("Insufficient balance!")
        return

    # Define the chance of winning the jackpot (e.g., 5%)
    jackpot_chance = 5

    if random.randint(1, 100) <= jackpot_chance:
        # Jackpot! Randomize the winning amount within a larger range
        min_jackpot_amount = amount * 5
        max_jackpot_amount = amount * 10
        winning_amount = random.randint(min_jackpot_amount, max_jackpot_amount)
        update_balance(user_id, winning_amount)
        await ctx.send(f"Jackpot! You won {winning_amount} coins! New balance is {balance + winning_amount} coins.")
    else:
        # Normal win/loss scenario
        min_normal_win_amount = int(amount * 0.75)  # 50% of the amount
        max_normal_win_amount = int(amount * 1.75)  # 150% of the amount
        winning_amount = random.randint(min_normal_win_amount, max_normal_win_amount)
        if random.choice([True, False]):
            update_balance(user_id, winning_amount)
            await ctx.send(f"You won {winning_amount} coins! New balance is {balance + winning_amount} coins.")
        else:
            update_balance(user_id, -amount)
            await ctx.send(f"You lost {amount} coins. New balance is {balance - amount} coins.")



@client.command()
async def rob(ctx, member: discord.Member):
    user_id = ctx.author.id
    target_id = member.id
    balance = get_balance(user_id)
    target_balance = get_balance(target_id)

    if target_balance < 100:
        await ctx.send(f"{member.name} doesn't have enough coins to rob!")
        return

    robbed_amount = random.randint(50, target_balance)
    update_balance(user_id, robbed_amount)
    update_balance(target_id, -robbed_amount)
    await ctx.send(f"You robbed {robbed_amount} coins from {member.name}! Your new balance is {balance + robbed_amount} coins.")

@client.command()
async def give(ctx, member: discord.Member, amount: int):
    user_id = ctx.author.id
    target_id = member.id
    balance = get_balance(user_id)

    if amount <= 0:
        await ctx.send("Amount must be positive!")
        return
    if amount > balance:
        await ctx.send("Insufficient balance!")
        return

    update_balance(user_id, -amount)
    update_balance(target_id, amount)
    await ctx.send(f"You gave {amount} coins to {member.name}. Your new balance is {balance - amount} coins.")

@client.command()
async def daily(ctx):
    user_id = ctx.author.id
    now = datetime.datetime.utcnow()
    c.execute('SELECT last_claimed FROM daily_rewards WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    
    if result:
        last_claimed = datetime.datetime.fromisoformat(result[0])
        if (now - last_claimed).days < 1:
            await ctx.send("You have already claimed your daily reward. Try again later.")
            return
    
    daily_amount = random.randint(100, 2000)
    update_balance(user_id, daily_amount)
    c.execute('REPLACE INTO daily_rewards (user_id, last_claimed) VALUES (?, ?)', (user_id, now.isoformat()))
    conn.commit()
    await ctx.send(f"You have claimed your daily reward of {daily_amount} coins! New balance is {get_balance(user_id)} coins.")

@client.command()
async def work(ctx):
    user_id = ctx.author.id
    if random.randint(1, 10) > 1:  # 90% chance to earn money
        earned_amount = random.randint(50, 150)
        update_balance(user_id, earned_amount)
        await ctx.send(f"You worked and earned {earned_amount} coins! New balance is {get_balance(user_id)} coins.")
    else:  # 10% chance to get fined
        fine_amount = random.randint(20, 50)
        update_balance(user_id, -fine_amount)
        await ctx.send(f"You got fined for breaking office supplies and lost {fine_amount} coins! New balance is {get_balance(user_id)} coins.")

@client.command()
async def crime(ctx):
    user_id = ctx.author.id
    if random.randint(1, 10) > 2:  # 80% chance to succeed
        crime_amount = random.randint(500, 1200)
        update_balance(user_id, crime_amount)
        await ctx.send(f"You committed a crime and earned {crime_amount} coins! New balance is {get_balance(user_id)} coins.")
    else:  # 20% chance to get caught
        caught_amount = random.randint(800, 2000)
        update_balance(user_id, -caught_amount)
        await ctx.send(f"You got caught during the crime and fined {caught_amount} coins! New balance is {get_balance(user_id)} coins.")

@client.command()
async def ping(ctx):
    ping_embed = discord.Embed(
        title="Ping",
        description="Pong!",
        color=discord.Color.blurple()
    )
    ping_embed.add_field(
        name=f"{client.user.name}'s Latency (ms): ",
        value=f"{round(client.latency * 1000)}ms.",
        inline=False
    )
    ping_embed.set_footer(
        text=f"Requested by {ctx.author.name}.",
        icon_url=ctx.author.avatar.url
    )
    await ctx.send(embed=ping_embed)

@client.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f'User {member.mention} has been kicked. Reason: {reason}')

@client.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(member.avatar.url)

@client.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(
        title=f"{member.name}'s Info",
        color=discord.Color.blue()
    )
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Name", value=member.display_name)
    embed.add_field(
        name="Account Created",
        value=member.created_at.strftime("%d/%m/%Y %H:%M:%S")
    )
    embed.add_field(
        name="Joined Server",
        value=member.joined_at.strftime("%d/%m/%Y %H:%M:%S")
    )
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@client.command()
@commands.has_permissions(ban_members=True)
async def exit(ctx):
    await ctx.send("Bot shutting down.. (I need to be manually restarted)")
    await client.close()

@client.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f'User {member.mention} has been banned. Reason: {reason}')

@client.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason=None):
    guild = ctx.guild
    muted_role = discord.utils.get(guild.roles, name="Muted")

    if not muted_role:
        muted_role = await guild.create_role(name="Muted")

        for channel in guild.channels:
            await channel.set_permissions(muted_role,
                                          speak=False,
                                          send_messages=False,
                                          read_message_history=True,
                                          read_messages=False)

    await member.add_roles(muted_role, reason=reason)
    await ctx.send(f'User {member.mention} has been muted. Reason: {reason}')

# Capture errors and store in the errors list
@client.event
async def on_command_error(ctx, error):
    error_message = f"Error in command '{ctx.command}': {error}"
    errors.append(error_message)
    print(error_message)  # Log the error in the terminal
    await ctx.send(error_message)

@kick.error
@ban.error
@mute.error
async def command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have the necessary permissions to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please specify a member to kick/ban/mute.")

@client.command(name='8ball')
async def eight_ball(ctx, *, question):
    responses = [
        "It is certain.", "It is decidedly so.", "Without a doubt.",
        "Yes definitely.", "You may rely on it.", "As I see it, yes.",
        "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
        "Reply hazy, try again.", "Ask again later.",
        "Better not tell you now.", "Cannot predict now.",
        "Concentrate and ask again.", "Don't count on it.", "My reply is no.",
        "My sources say no.", "Outlook not so good.", "Very doubtful."
    ]
    response = random.choice(responses)
    await ctx.send(f'Question: {question}\nAnswer: {response}')

@client.command()
async def roll(ctx):
    rolls = 1
    limit = 6

    result = ', '.join(str(random.randint(1, limit)) for _ in range(rolls))
    await ctx.send(result)

@tasks.loop(seconds=5)
async def update_latency():
    latency = round(client.latency * 1000)
    latency_values.append(latency)
    if len(latency_values) > 100:
        latency_values.pop(0)

@client.command()
@commands.has_permissions(kick_members=True)
async def admin(ctx):
    uptime = datetime.datetime.utcnow() - start_time
    guild_count = len(client.guilds)
    user_count = sum(guild.member_count for guild in client.guilds)

    if latency_values:
        min_latency = min(latency_values)
        max_latency = max(latency_values)
    else:
        min_latency = max_latency = round(client.latency * 1000)

    filename = os.path.basename(__file__)
    running_status = "Running Online" if filename == "main.py" else "Running Locally"
    embed = discord.Embed(title="Bot Admin Information", color=discord.Color.gold())
    embed.add_field(name="Uptime", value=str(uptime), inline=False)
    embed.add_field(name="Servers", value=guild_count, inline=False)
    embed.add_field(name="Users", value=user_count, inline=False)
    embed.add_field(name="Latency", value=f"{round(client.latency * 1000)} ms (Min: {min_latency} ms, Max: {max_latency} ms)", inline=False)
    embed.add_field(name="Environment", value=running_status, inline=False)

    error_field_value = "\n".join(errors[-10:]) if errors else "No errors."
    embed.add_field(name="Errors", value=error_field_value, inline=False)
    
    embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)

    await ctx.send(embed=embed)

@client.command()
async def coinflip(ctx):
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"The coin landed on: {result}")

@client.command()
async def meme(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://www.reddit.com/r/memes/random/.json") as response:
            if response.status == 200:
                data = await response.json()
                meme_url = data[0]['data']['children'][0]['data']['url']
                await ctx.send(meme_url)
            else:
                await ctx.send("meme problem, uh oh!! contact @axolott__.")

@client.command()
async def poll(ctx, *, question):
    embed = discord.Embed(title="Poll", description=question, color=discord.Color.blue())
    message = await ctx.send(embed=embed)
    await message.add_reaction('??')
    await message.add_reaction('??')

@client.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    await ctx.channel.purge(limit=amount)
    await ctx.send(f"Cleared {amount} messages.", delete_after=5)

@client.command()
async def statistics(ctx):
    cpu_usage = psutil.cpu_percent(interval=1)
    ram_usage = psutil.virtual_memory()
    disk_usage = psutil.disk_usage('/')
    
    temperature = "N/A"
    try:
        if platform.system() == "Linux":
            # Check for Raspberry Pi
            if os.path.isfile("/sys/class/thermal/thermal_zone0/temp"):
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    temp = int(f.read()) / 1000
                    temperature = f"{temp:.1f}C"
            else:
                temp_output = subprocess.check_output(["sensors"]).decode()
                for line in temp_output.split("\n"):
                    if "temp1" in line:
                        temp = float(line.split("+")[1].split("C")[0])
                        temperature = f"{temp:.1f}C"
                        break
        elif platform.system() == "Windows":
            # Windows temperature (requires third-party tools or admin privileges)
            temp_output = subprocess.check_output(["wmic", "temperature"]).decode()
            for line in temp_output.split("\n"):
                if "Temperature" in line:
                    temp = float(line.split()[1]) / 10.0
                    temperature = f"{temp:.1f}C"
                    break
    except Exception as e:
        print(f"Failed to get temperature: {e}")
    
    embed = discord.Embed(title="System Statistics", color=discord.Color.blue())
    embed.add_field(name="CPU Usage", value=f"{cpu_usage}%", inline=False)
    embed.add_field(name="RAM Usage", value=f"{ram_usage.percent}% ({ram_usage.used / (1024 ** 3):.2f} GB / {ram_usage.total / (1024 ** 3):.2f} GB)", inline=False)
    embed.add_field(name="Disk Space Used", value=f"{disk_usage.percent}% ({disk_usage.used / (1024 ** 3):.2f} GB / {disk_usage.total / (1024 ** 3):.2f} GB)", inline=False)
    embed.add_field(name="Temperature", value=temperature, inline=False)
    
    await ctx.send(embed=embed)

# New commands
@client.command()
async def cat(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://www.reddit.com/r/catpictures/random/.json") as response:
            if response.status == 200:
                data = await response.json()
                cat_url = data[0]['data']['children'][0]['data']['url']
                await ctx.send(cat_url)
            else:
                await ctx.send("Couldn't fetch a cat image, please try again.")

@client.command()
async def dog(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://www.reddit.com/r/dogpictures/random/.json") as response:
            if response.status == 200:
                data = await response.json()
                dog_url = data[0]['data']['children'][0]['data']['url']
                await ctx.send(dog_url)
            else:
                await ctx.send("Couldn't fetch a dog image, please try again.")

@client.command()
async def joke(ctx):
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "Why was the math book sad? It had too many problems.",
        "What do you call fake spaghetti? An impasta!"
    ]
    await ctx.send(random.choice(jokes))

@client.command()
async def quote(ctx):
    quotes = [
        "The best way to predict the future is to invent it. - Alan Kay",
        "Life is 10% what happens to us and 90% how we react to it. - Charles R. Swindoll",
        "The only way to do great work is to love what you do. - Steve Jobs"
    ]
    await ctx.send(random.choice(quotes))

@client.command()
async def fact(ctx):
    facts = [
        "Honey never spoils.",
        "A day on Venus is longer than a year on Venus.",
        "Bananas are berries, but strawberries aren't."
    ]
    await ctx.send(random.choice(facts))

@client.command()
async def advice(ctx):
    advice_list = [
        "Never let your sense of morals prevent you from doing what is right.",
        "You can't control how other people receive your energy. Anything you do or say gets filtered through the lens of whatever personal stuff they are going through at the moment."
    ]
    await ctx.send(random.choice(advice_list))

@client.command()
async def compliment(ctx):
    compliments = [
        "You're like a ray of sunshine on a really dreary day.",
        "You are making a difference.",
        "You bring out the best in other people."
    ]
    await ctx.send(random.choice(compliments))

@client.command()
async def insult(ctx):
    insults = [
        "You're not stupid; you just have bad luck thinking.",
        "You bring everyone so much joy when you leave the room."
    ]
    await ctx.send(random.choice(insults))

@client.command()
async def rps(ctx, choice: str):
    rps_choices = ['rock', 'paper', 'scissors']
    bot_choice = random.choice(rps_choices)
    if choice not in rps_choices:
        await ctx.send("Invalid choice! Choose rock, paper, or scissors.")
    else:
        if choice == bot_choice:
            result = "It's a tie!"
        elif (choice == 'rock' and bot_choice == 'scissors') or (choice == 'paper' and bot_choice == 'rock') or (choice == 'scissors' and bot_choice == 'paper'):
            result = "You win!"
        else:
            result = "You lose!"
        await ctx.send(f"You chose {choice}, I chose {bot_choice}. {result}")

@client.command()
async def say(ctx, *, message: str):
    await ctx.send(message)

@client.command()
async def reverse(ctx, *, message: str):
    await ctx.send(message[::-1])

@client.command()
async def choose(ctx, *choices: str):
    if not choices:
        await ctx.send("Please provide some choices!")
    else:
        await ctx.send(random.choice(choices))

@client.command()
async def invert(ctx, member: discord.Member = None):
    member = member or ctx.author
    avatar_url = member.avatar.url
    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url) as response:
            if response.status == 200:
                data = io.BytesIO(await response.read())
                with Image.open(data) as img:
                    inverted_image = ImageOps.invert(img.convert("RGB"))
                    with io.BytesIO() as image_binary:
                        inverted_image.save(image_binary, 'PNG')
                        image_binary.seek(0)
                        await ctx.send(file=discord.File(fp=image_binary, filename='inverted.png'))
            else:
                await ctx.send("Could not retrieve the avatar.")



@client.command()
async def quiz(ctx):
    questions = [
        {"question": "What is 2 + 2?", "options": ["3", "4", "5", "6"], "answer": "4"},
        {"question": "What is the capital of France?", "options": ["London", "Paris", "Berlin", "Rome"], "answer": "Paris"},
        {"question": "Who wrote 'Romeo and Juliet'?", "options": ["William Shakespeare", "Charles Dickens", "Jane Austen", "Mark Twain"], "answer": "William Shakespeare"},
        {"question": "What year did World War I begin?", "options": ["1914", "1918", "1939", "1945"], "answer": "1914"},
        {"question": "What is the chemical symbol for gold?", "options": ["Au", "Ag", "Fe", "Cu"], "answer": "Au"},
        {"question": "What is the tallest mountain in the world?", "options": ["Mount Everest", "K2", "Kangchenjunga", "Lhotse"], "answer": "Mount Everest"},
        {"question": "Who painted the Mona Lisa?", "options": ["Leonardo da Vinci", "Vincent van Gogh", "Pablo Picasso", "Michelangelo"], "answer": "Leonardo da Vinci"},
        {"question": "Which planet is known as the Red Planet?", "options": ["Mars", "Venus", "Jupiter", "Saturn"], "answer": "Mars"},
        {"question": "What is the largest organ in the human body?", "options": ["Skin", "Heart", "Liver", "Lung"], "answer": "Skin"},
        {"question": "What is the chemical formula for water?", "options": ["H2O", "CO2", "O2", "CH4"], "answer": "H2O"}
    ]

    random.shuffle(questions)
    score = 0

    for q in questions:
        options = '\n'.join([f"{i}. {option}" for i, option in enumerate(q['options'], start=1)])
        embed = discord.Embed(
            title="Quiz Time!",
            description=q['question'],
            color=discord.Color.orange()
        )
        embed.add_field(name="Options:", value=options, inline=False)
        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            response = await client.wait_for('message', timeout=30, check=check)
            if response.content.lower() == q['answer'].lower():
                await ctx.send("Correct!")
                score += 1
            else:
                await ctx.send(f"Incorrect! The correct answer is: {q['answer']}")
        except asyncio.TimeoutError:
            await ctx.send("Time's up! Quiz ended.")
            break

    await ctx.send(f"Quiz ended. You scored {score}/{len(questions)}.")

client.run(TOKEN)