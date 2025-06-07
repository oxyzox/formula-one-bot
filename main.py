import discord
import requests
import os
import datetime
import pytz
import asyncio
from discord.ext import commands, tasks
from dotenv import load_dotenv
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch

load_dotenv()  # Load token from .env file
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Create bot with increased privileges for reactions, message history, etc.
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Team colors for consistent visual branding
TEAM_COLORS = {
    "Red Bull": 0x0600EF,
    "Ferrari": 0xDC0000,
    "Mercedes": 0x00D2BE,
    "McLaren": 0xFF8700,
    "Aston Martin": 0x006F62,
    "Alpine": 0x0090FF,
    "Williams": 0x005AFF,
    "AlphaTauri": 0x2B4562,
    "Alfa Romeo": 0x900000,
    "Haas F1 Team": 0xFFFFFF,
    "Racing Point": 0xF596C8,
    "Renault": 0xFFF500,
    "Toro Rosso": 0x469BFF,
    "Sauber": 0x9B0000,
    "Force India": 0xFF5F0F,
    "Manor Marussia": 0x6E0000,
    "Lotus F1": 0x000000,
    "Marussia": 0x6E0000,
    "Caterham": 0x006C00,
    "HRT": 0x686868,
    "Virgin": 0x323232,
    "Brawn": 0xF0F0F0,
    "Honda": 0x006633,
    "Super Aguri": 0xE20B00,
    "BMW Sauber": 0x6CD3BF,
    "Spyker": 0xF24013,
    "Midland": 0x9E0000,
    "Jordan": 0xF9CB46,
    "Jaguar": 0x358C75,
    "BAR": 0xFDB000,
    "Arrows": 0xFF8000,
    "Minardi": 0x000000,
    "Prost": 0x00005F,
    "Benetton": 0x00841F,
    "Stewart": 0xFFFFFF,
    "Tyrrell": 0x3A36DB,
    "Footwork": 0xFF8000,
    "Ligier": 0x00007D,
    "Simtek": 0xFFFFFF,
    "Larrousse": 0xFFFFFF,
    "Brabham": 0x487890,
    "Fondmetal": 0xFFFFFF,
    "March": 0x8D0060,
    "Forti": 0xFF7F00,
    "Pacific": 0x006633,
    "RB F1 Team": 0x0600EF,  # Alias for Red Bull in newer seasons
    "Racing Bulls": 0x0600EF,  # Alias for RB
    "Haas": 0xFFFFFF,  # Shortened name alias
    "AlphaTauri RB": 0x0600EF,  # Alias
}

# Default color if team not found
DEFAULT_COLOR = 0xFF5733

# Cache for API responses to reduce API calls
cache = {}
CACHE_EXPIRY = 3600  # seconds

@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync slash commands
    print(f"🚀 Bot is online! Logged in as {bot.user}")
    print(f"🔗 Invite link: https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="F1 races 🏎️"))

def get_cached_response(url, force_refresh=False):
    """Get cached response or fetch from API and cache it"""
    current_time = datetime.datetime.now().timestamp()
    
    if url in cache and not force_refresh:
        cached_data, timestamp = cache[url]
        if current_time - timestamp < CACHE_EXPIRY:
            return cached_data
    
    response = requests.get(url).json()
    cache[url] = (response, current_time)
    return response

def get_team_color(team_name):
    """Get team color or default if not found"""
    if not team_name:
        return DEFAULT_COLOR
        
    # Try exact match first
    if team_name in TEAM_COLORS:
        return TEAM_COLORS[team_name]
    
    # Try partial match
    for team, color in TEAM_COLORS.items():
        if team.lower() in team_name.lower() or team_name.lower() in team.lower():
            return color
    
    return DEFAULT_COLOR

def create_progress_bar(position, total_drivers, width=20):
    """Create a text-based progress bar based on position"""
    position = int(position)
    progress = max(0, (total_drivers - position) / (total_drivers - 1))
    filled = int(width * progress)
    progress_bar = '█' * filled + '░' * (width - filled)
    return progress_bar

# 🏎️ Fetch race results with detailed embed and position visualization
@bot.tree.command(name="f1_results", description="Get F1 race results for a specific year and round")
async def f1_results(interaction: discord.Interaction, year: int, round: int):
    await interaction.response.defer()
    
    url = f"https://ergast.com/api/f1/{year}/{round}/results.json"
    response = get_cached_response(url)

    try:
        race_data = response["MRData"]["RaceTable"]["Races"][0]
        race_name = race_data["raceName"]
        circuit = race_data["Circuit"]["circuitName"]
        country = race_data["Circuit"]["Location"]["country"]
        date = race_data["date"]
        
        # First create the main embed
        main_embed = discord.Embed(
            title=f"🏁 {race_name} {year}", 
            description=f"📍 **Circuit:** {circuit}, {country}\n📅 **Date:** {date}", 
            color=0xFF5733
        )
        
        # Add circuit image if available (placeholder)
        main_embed.set_thumbnail(url=f"https://via.placeholder.com/150?text={circuit.replace(' ', '+')}")
        
        # Add podium section
        podium_text = ""
        
        total_drivers = len(race_data["Results"])
        
        # Process all results for detailed display
        results = []
        fastest_lap_driver = None
        fastest_lap_time = None
        
        for driver in race_data["Results"]:
            position = driver["position"]
            position_int = int(position)
            driver_id = driver["Driver"]["driverId"]
            name = f"{driver['Driver']['givenName']} {driver['Driver']['familyName']}"
            team = driver["Constructor"]["name"]
            team_color = get_team_color(team)
            
            # Check if driver has the fastest lap
            if "FastestLap" in driver:
                lap_time = driver["FastestLap"]["Time"]["time"]
                lap_number = driver["FastestLap"]["lap"]
                lap_rank = driver["FastestLap"]["rank"]
                
                if lap_rank == "1":
                    fastest_lap_driver = name
                    fastest_lap_time = lap_time
            
            # Time or status (DNF, DSQ, etc.)
            if "Time" in driver:
                time_or_status = driver["Time"]["time"]
            elif "status" in driver:
                time_or_status = f"⚠️ {driver['status']}"
            else:
                time_or_status = "N/A"
            
            # For podium positions, add to podium section with emoji
            if position_int <= 3:
                medal = ["🥇", "🥈", "🥉"][position_int - 1]
                podium_text += f"{medal} **{name}** ({team})\n"
            
            # Add progress bar for visual representation
            progress = create_progress_bar(position, total_drivers)
            
            # Create the detailed result entry
            result_entry = f"**{position}.** {name} ({team})\n⏱️ {time_or_status}\n{progress}\n"
            results.append((position_int, result_entry, team_color))
        
        # Add podium to main embed
        if podium_text:
            main_embed.add_field(name="🏆 Podium", value=podium_text, inline=False)
        
        # Add fastest lap info if available
        if fastest_lap_driver and fastest_lap_time:
            main_embed.add_field(name="⚡ Fastest Lap", value=f"{fastest_lap_driver} - {fastest_lap_time}", inline=False)
        
        # Add footer with API attribution
        main_embed.set_footer(text=f"Data provided by Ergast API • {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Send the main embed
        await interaction.followup.send(embed=main_embed)
        
        # Sort results by position
        results.sort(key=lambda x: x[0])
        
        # Create separate embeds for results (grouped to avoid hitting Discord's limits)
        chunks = [results[i:i+7] for i in range(0, len(results), 7)]
        
        for i, chunk in enumerate(chunks):
            positions = [r[0] for r in chunk]
            start_pos = min(positions)
            end_pos = max(positions)
            
            result_embed = discord.Embed(
                title=f"Positions {start_pos}-{end_pos}",
                color=0x1E90FF
            )
            
            for _, result_text, team_color in chunk:
                result_embed.add_field(name="\u200b", value=result_text, inline=True)
                result_embed.color = team_color  # Use the last team's color for the embed
            
            await interaction.followup.send(embed=result_embed)

    except (IndexError, KeyError) as e:
        await interaction.followup.send(f"❌ Could not fetch race results. Please check the year and round number. Error: {str(e)}")

# 🏆 Fetch driver standings with visualization
@bot.tree.command(name="f1_standings_drivers", description="Get F1 driver standings for a specific year with graph visualization")
async def f1_standings_drivers(interaction: discord.Interaction, year: int):
    await interaction.response.defer()

    url = f"https://ergast.com/api/f1/{year}/driverStandings.json"
    response = get_cached_response(url)

    try:
        standings = response["MRData"]["StandingsTable"]["StandingsLists"][0]["DriverStandings"]
        
        # Create visualization of driver standings
        plt.figure(figsize=(12, 8))
        plt.style.use('dark_background')
        
        drivers = []
        points = []
        colors = []
        
        # Only use top 15 drivers for better visualization
        for driver in standings[:15]:
            name = f"{driver['Driver']['givenName'][0]}. {driver['Driver']['familyName']}"
            points_val = float(driver["points"])
            
            # Get team color for consistent branding
            team = driver["Constructors"][0]["name"] if driver["Constructors"] else "Unknown Team"
            team_color = get_team_color(team)
            
            # Convert Discord color to matplotlib RGB
            r = ((team_color >> 16) & 255) / 255
            g = ((team_color >> 8) & 255) / 255
            b = (team_color & 255) / 255
            
            drivers.append(name)
            points.append(points_val)
            colors.append((r, g, b))
        
        # Reverse lists to show highest points at the top
        drivers.reverse()
        points.reverse()
        colors.reverse()
        
        # Create horizontal bar chart
        bars = plt.barh(drivers, points, color=colors, height=0.6)
        
        # Add point values at the end of each bar
        for bar in bars:
            width = bar.get_width()
            plt.text(width + max(points)/50, bar.get_y() + bar.get_height()/2, 
                    f'{width:.0f}', va='center')
        
        # Create custom legend for teams
        legend_elements = []
        teams_added = set()
        
        for i, driver in enumerate(standings[:15]):
            if "Constructors" in driver and driver["Constructors"]:
                team = driver["Constructors"][0]["name"]
                if team not in teams_added:
                    teams_added.add(team)
                    team_color = get_team_color(team)
                    
                    # Convert Discord color to matplotlib RGB
                    r = ((team_color >> 16) & 255) / 255
                    g = ((team_color >> 8) & 255) / 255
                    b = (team_color & 255) / 255
                    
                    legend_elements.append(
                        Patch(facecolor=(r, g, b), label=team)
                    )
        
        plt.legend(handles=legend_elements, loc='lower right')
        plt.xlabel('Points', fontweight='bold')
        plt.title(f'{year} Formula 1 Driver Standings', fontweight='bold', fontsize=16)
        plt.grid(axis='x', linestyle='--', alpha=0.3)
        plt.tight_layout()
        
        # Save to bytes buffer
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        
        # Create file to send
        chart_file = discord.File(buf, filename="driver_standings.png")
        
        # Create embed with chart
        embed = discord.Embed(
            title=f"🏎️ {year} Formula 1 Driver Championship", 
            description=f"Points standings for the {year} F1 season",
            color=0x1E90FF
        )
        embed.set_image(url="attachment://driver_standings.png")
        
        # Add top 3 drivers with their colors as fields
        for i, driver in enumerate(standings[:3]):
            position = driver["position"]
            name = f"{driver['Driver']['givenName']} {driver['Driver']['familyName']}"
            points = driver["points"]
            team = driver["Constructors"][0]["name"] if driver["Constructors"] else "Unknown Team"
            team_color_hex = hex(get_team_color(team))[2:].zfill(6)
            medal = ["🥇", "🥈", "🥉"][i]
            
            embed.add_field(
                name=f"{medal} #{position} {name}", 
                value=f"**{points} points** ({team})", 
                inline=True
            )
        
        # Add total championship count for top drivers if available
        try:
            for driver in standings[:3]:
                driver_id = driver["Driver"]["driverId"]
                championships_url = f"https://ergast.com/api/f1/drivers/{driver_id}/driverStandings/1.json"
                championships_data = get_cached_response(championships_url)
                championships = int(championships_data["MRData"]["total"])
                
                if championships > 0:
                    name = f"{driver['Driver']['givenName']} {driver['Driver']['familyName']}"
                    embed.add_field(
                        name=f"🏆 Championships", 
                        value=f"{name}: {championships}",
                        inline=False
                    )
                    break  # Just add for the first driver with championships
        except Exception as e:
            # Silently ignore if championship data isn't available
            pass
        
        embed.set_footer(text=f"Data provided by Ergast API • {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        await interaction.followup.send(embed=embed, file=chart_file)
        
    except Exception as e:
        # Fallback to text-based standings if visualization fails
        try:
            results = []
            
            for driver in standings[:10]:  # Top 10 drivers
                position = driver["position"]
                name = f"{driver['Driver']['givenName']} {driver['Driver']['familyName']}"
                points = driver["points"]
                team = driver["Constructors"][0]["name"] if driver["Constructors"] else "Unknown Team"
                
                results.append(f"**#{position}** {name} ({team}) - {points} pts 🏅")
            
            fallback_embed = discord.Embed(
                title=f"🏎️ {year} Driver Standings", 
                description="\n".join(results), 
                color=0x1E90FF
            )
            fallback_embed.set_footer(text="Data provided by Ergast API")
            
            await interaction.followup.send(embed=fallback_embed)
            
        except (IndexError, KeyError) as e:
            await interaction.followup.send(f"❌ Could not fetch driver standings. Please check the year. Error: {str(e)}")
            

# 🏢 Fetch team standings with visualization
@bot.tree.command(name="f1_standings_teams", description="Get F1 constructor standings for a specific year")
async def f1_standings_teams(interaction: discord.Interaction, year: int):
    await interaction.response.defer()
    
    url = f"https://ergast.com/api/f1/{year}/constructorStandings.json"
    response = get_cached_response(url)

    try:
        standings = response["MRData"]["StandingsTable"]["StandingsLists"][0]["ConstructorStandings"]
        
        # Create graph for team standings visualization
        try:
            # Create team standings bar chart
            plt.figure(figsize=(10, 6))
            plt.style.use('dark_background')
            
            teams = []
            points = []
            colors = []
            
            for team in standings[:10]:
                team_name = team["Constructor"]["name"]
                team_points = float(team["points"])
                team_color = get_team_color(team_name)
                
                # Convert Discord color to matplotlib RGB
                r = ((team_color >> 16) & 255) / 255
                g = ((team_color >> 8) & 255) / 255
                b = (team_color & 255) / 255
                
                teams.append(team_name)
                points.append(team_points)
                colors.append((r, g, b))
            
            # Reverse lists to show highest points at the top
            teams.reverse()
            points.reverse()
            colors.reverse()
            
            # Create horizontal bar chart
            bars = plt.barh(teams, points, color=colors, height=0.6)
            
            # Add point values at the end of each bar
            for bar in bars:
                width = bar.get_width()
                plt.text(width + 5, bar.get_y() + bar.get_height()/2, 
                        f'{width:.0f}', va='center')
            
            plt.xlabel('Points', fontweight='bold')
            plt.title(f'{year} Formula 1 Constructor Standings', fontweight='bold', fontsize=14)
            plt.tight_layout()
            
            # Save to bytes buffer
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()
            
            # Create file to send
            chart_file = discord.File(buf, filename="team_standings.png")
            
            # Create embed with chart
            embed = discord.Embed(
                title=f"🏁 {year} Constructor Standings", 
                description=f"Team standings for the {year} Formula 1 season",
                color=0xFFD700
            )
            embed.set_image(url="attachment://team_standings.png")
            
            # Add top 3 teams with their colors
            for i, team in enumerate(standings[:3]):
                position = team["position"]
                name = team["Constructor"]["name"]
                points = team["points"]
                team_color_hex = hex(get_team_color(name))[2:].zfill(6)
                medal = ["🥇", "🥈", "🥉"][i]
                
                embed.add_field(
                    name=f"{medal} #{position} {name}", 
                    value=f"**{points} points**", 
                    inline=True
                )
            
            embed.set_footer(text=f"Data provided by Ergast API • {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            await interaction.followup.send(embed=embed, file=chart_file)
            
        except Exception as e:
            # Fallback to text-based standings if visualization fails
            print(f"Visualization error: {str(e)}")
            results = []
            
            try:
                max_points = float(standings[0]["points"])  # Leader's points
            except:
                max_points = 100  # Fallback
                
            for team in standings:
                position = team["position"]
                name = team["Constructor"]["name"]
                points = team["points"]
                
                # Create visual points bar
                try:
                    points_float = float(points)
                    percentage = min(100, max(0, (points_float / max_points) * 100))
                except:
                    percentage = 0
                    
                points_bar = "█" * int(percentage/5) + "░" * (20 - int(percentage/5))
                
                results.append(f"**#{position}** {name} - {points} pts\n{points_bar}")
            
            embed = discord.Embed(
                title=f"🏁 {year} Constructor Standings", 
                description="\n\n".join(results[:10]), 
                color=0xFFD700
            )
            embed.set_footer(text=f"Data provided by Ergast API • {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            await interaction.followup.send(embed=embed)

    except (IndexError, KeyError) as e:
        await interaction.followup.send(f"❌ Could not fetch constructor standings. Please check the year. Error: {str(e)}")

# 📅 Fetch next race with countdown and circuit info
@bot.tree.command(name="f1_next", description="Get detailed info about the next F1 event")
async def f1_next(interaction: discord.Interaction):
    await interaction.response.defer()
    
    url = "https://ergast.com/api/f1/current/next.json"
    response = get_cached_response(url, force_refresh=True)  # Force refresh for latest info

    try:
        race = response["MRData"]["RaceTable"]["Races"][0]
        race_name = race["raceName"]
        circuit = race["Circuit"]["circuitName"]
        country = race["Circuit"]["Location"]["country"]
        locality = race["Circuit"]["Location"]["locality"]
        date = race["date"]
        time = race["time"].replace("Z", "")
        
        # Parse date and time
        race_datetime_str = f"{date}T{time}"
        race_datetime = datetime.datetime.fromisoformat(race_datetime_str)
        race_datetime = pytz.utc.localize(race_datetime)
        
        # Calculate time until race
        now = datetime.datetime.now(pytz.utc)
        time_diff = race_datetime - now
        
        # Format time difference
        if time_diff.total_seconds() > 0:
            days = time_diff.days
            hours, remainder = divmod(time_diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            countdown = f"🕒 **Countdown:** {days}d {hours}h {minutes}m {seconds}s"
        else:
            countdown = "🏁 **Race has started or completed**"
        
        # Get session data if available
        sessions = []
        for session_type in ["FirstPractice", "SecondPractice", "ThirdPractice", "Qualifying", "Sprint"]:
            if session_type in race:
                session_data = race[session_type]
                session_date = session_data["date"]
                session_time = session_data["time"].replace("Z", "")
                
                # Parse session datetime
                session_datetime_str = f"{session_date}T{session_time}"
                session_datetime = datetime.datetime.fromisoformat(session_datetime_str)
                session_datetime = pytz.utc.localize(session_datetime)
                
                session_name = session_type
                if session_type == "FirstPractice":
                    session_name = "Practice 1"
                elif session_type == "SecondPractice":
                    session_name = "Practice 2"
                elif session_type == "ThirdPractice":
                    session_name = "Practice 3"
                
                # Format display and add to sessions list
                sessions.append((session_name, session_datetime))
        
        # Add race to sessions list
        sessions.append(("Race", race_datetime))
        
        # Get circuit coordinates if available
        lat = race["Circuit"]["Location"].get("lat", "")
        long = race["Circuit"]["Location"].get("long", "")
        
        # Create embed with all collected info
        embed = discord.Embed(
            title=f"📅 Next F1 Event: {race_name}", 
            color=0x00FF00,
            description=f"{countdown}\n\n**📍 Circuit:** {circuit}, {locality}, {country} 🏎️\n"
        )
        
        # Add circuit map if coordinates are available
        if lat and long:
            map_url = f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{long}&zoom=14&size=400x200&maptype=roadmap&markers=color:red%7C{lat},{long}&key=YOUR_GOOGLE_MAPS_API_KEY"
            embed.set_thumbnail(url=f"https://via.placeholder.com/200x100?text={circuit.replace(' ', '+')}")
        
        # Add session times as fields
        for session_name, session_time in sessions:
            # Format time with timezone
            time_str = session_time.strftime("%Y-%m-%d %H:%M UTC")
            
            # Check if session is in the past
            status = "✅" if session_time < now else "⏳"
            
            embed.add_field(
                name=f"{status} {session_name}",
                value=time_str,
                inline=True
            )
        
        embed.set_footer(text=f"Data provided by Ergast API • {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        await interaction.followup.send(embed=embed)

    except (IndexError, KeyError) as e:
        await interaction.followup.send(f"❌ Could not fetch the next race details. Error: {str(e)}")

# 🔍 Search for a driver
@bot.tree.command(name="f1_driver", description="Search for an F1 driver")
async def f1_driver(interaction: discord.Interaction, name: str):
    url = f"https://ergast.com/api/f1/drivers/{name}.json"
    response = requests.get(url).json()

    try:
        driver = response["MRData"]["DriverTable"]["Drivers"][0]
        full_name = f"{driver['givenName']} {driver['familyName']}"
        nationality = driver["nationality"]
        birth_date = driver["dateOfBirth"]
        wiki_url = driver["url"]

        embed = discord.Embed(title=f"🏎️ {full_name}", color=0x3498DB, url=wiki_url)
        embed.add_field(name="🌍 Nationality", value=nationality, inline=True)
        embed.add_field(name="🎂 Birth Date", value=birth_date, inline=True)
        embed.add_field(name="📖 More Info", value=f"[Wikipedia]({wiki_url})", inline=False)
        embed.set_footer(text="Data provided by Ergast API")

        await interaction.response.send_message(embed=embed)

    except (IndexError, KeyError):
        await interaction.response.send_message("❌ Could not find the driver. Check the name and try again.")

bot.run(TOKEN)

