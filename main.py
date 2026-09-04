import os
import datetime
import discord
from discord import ui
from discord.ext import commands
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# --- Initialization & Config ---
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is missing! Check your .env file.")

REQUIRED_ROLE = "Caller"
SHEET_NAME = "Free Beer Comps"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(creds)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Global State Tracking ---
LAST_ANNOUNCED_TAB = None

# --- Helper Functions ---
def get_sheet():
    return gc.open(SHEET_NAME)

def get_or_create_responses_tab(sh):
    try:
        resp_sheet = sh.worksheet("Responses")
        headers = resp_sheet.row_values(1)
        if len(headers) < 6 or headers[5] != "Status":
            resp_sheet.update_cell(1, 6, "Status")
        return resp_sheet
    except Exception:
        resp_sheet = sh.add_worksheet(title="Responses", rows="1000", cols="6")
        resp_sheet.append_row(["Player", "Primary Preference", "Secondary Preference", "Tertiary Preference", "Is Fill", "Status"])
        return resp_sheet

def log_action(comp_name, player_name, action, details):
    try:
        sh = get_sheet()
        try:
            log_sheet = sh.worksheet("Audit Log")
        except Exception:
            log_sheet = sh.add_worksheet(title="Audit Log", rows="1000", cols="5")
            log_sheet.append_row(["Timestamp", "Comp Name", "Player", "Action", "Details"])

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_sheet.append_row([timestamp, comp_name, player_name, action, details])
    except Exception as e:
        print(f"Logging error: {e}")

def get_comp_weapons(comp_name):
    """Fetches unique weapons/roles directly from the chosen comp worksheet."""
    try:
        sh = get_sheet()
        sheet = sh.worksheet(comp_name)
        records = sheet.get_all_records()
        weapons = list(dict.fromkeys([str(row["Role / Weapon"]).strip() for row in records if row.get("Role / Weapon")]))
        return weapons[:25]  # Discord dropdown max limit is 25 items
    except Exception as e:
        print(f"Error fetching weapons for {comp_name}: {e}")
        return []

def assign_shotcaller_in_sheet(comp_name, shotcaller_name):
    """Finds the Shotcaller row in the target comp and updates Column C."""
    if not shotcaller_name:
        return False
    try:
        sh = get_sheet()
        sheet = sh.worksheet(comp_name)
        records = sheet.get_all_records()
        
        for idx, row in enumerate(records, start=2):
            role = str(row.get("Role / Weapon", "")).strip().lower()
            if role == "shotcaller":
                sheet.update_cell(idx, 3, shotcaller_name)
                log_action(comp_name, shotcaller_name, "Shotcaller Assigned", f"Pre-assigned via !comp modal to row {idx}")
                return True
        return False
    except Exception as e:
        print(f"Error assigning shotcaller: {e}")
        return False

# --- UI Components for Player Preference Selection ---

class DynamicWeaponSelect(ui.Select):
    def __init__(self, weapons, placeholder, pref_level):
        self.pref_level = pref_level
        options = [discord.SelectOption(label=w, value=w) for w in weapons]
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.selections[self.pref_level] = self.values[0]
        await interaction.response.defer()

class DynamicPreferenceView(ui.View):
    def __init__(self, comp_name, weapons):
        super().__init__(timeout=120)
        self.comp_name = comp_name
        self.selections = {"p1": None, "p2": "", "p3": ""}

        self.add_item(DynamicWeaponSelect(weapons, "Select 1st Preference (Primary)...", "p1"))
        if len(weapons) > 1:
            self.add_item(DynamicWeaponSelect(weapons, "Select 2nd Preference (Secondary - Optional)...", "p2"))
        if len(weapons) > 2:
            self.add_item(DynamicWeaponSelect(weapons, "Select 3rd Preference (Tertiary - Optional)...", "p3"))

    @ui.button(label="Submit Preferences", style=discord.ButtonStyle.success, row=4)
    async def confirm_submit(self, interaction: discord.Interaction, button: ui.Button):
        p1 = self.selections["p1"]
        p2 = self.selections["p2"]
        p3 = self.selections["p3"]

        if not p1:
            await interaction.response.send_message("❌ You must select at least a 1st Preference!", ephemeral=True)
            return

        user_name = interaction.user.display_name
        sh = get_sheet()
        resp_sheet = get_or_create_responses_tab(sh)
        records = resp_sheet.get_all_records()

        updated = False
        for idx, row in enumerate(records, start=2):
            if str(row["Player"]) == user_name:
                resp_sheet.update_cell(idx, 2, p1)
                resp_sheet.update_cell(idx, 3, p2)
                resp_sheet.update_cell(idx, 4, p3)
                resp_sheet.update_cell(idx, 5, "FALSE")
                resp_sheet.update_cell(idx, 6, "Pending")
                updated = True
                break

        if not updated:
            resp_sheet.append_row([user_name, p1, p2, p3, "FALSE", "Pending"])

        log_action(self.comp_name, user_name, "Preferences Saved", f"1: {p1} | 2: {p2 or 'None'} | 3: {p3 or 'None'}")
        await interaction.response.send_message(
            f"✅ Saved preferences for **{self.comp_name}**:\n1️⃣ **{p1}**\n2️⃣ **{p2 or 'None'}**\n3️⃣ **{p3 or 'None'}**",
            ephemeral=True
        )

class MultiPrefView(ui.View):
    def __init__(self, comp_name):
        super().__init__(timeout=None)
        self.comp_name = comp_name

    @ui.button(label="Submit Preferences", style=discord.ButtonStyle.primary, custom_id="pref_btn")
    async def open_preference_menu(self, interaction: discord.Interaction, button: ui.Button):
        weapons = get_comp_weapons(self.comp_name)
        if not weapons:
            await interaction.response.send_message("❌ Could not load weapons for this comp.", ephemeral=True)
            return

        pref_view = DynamicPreferenceView(self.comp_name, weapons)
        await interaction.response.send_message(
            content=f"🎯 **Select your weapon preferences for `{self.comp_name}`:**",
            view=pref_view,
            ephemeral=True
        )

    @ui.button(label="Sign Up as Fill", style=discord.ButtonStyle.secondary, custom_id="fill_btn")
    async def set_fill(self, interaction: discord.Interaction, button: ui.Button):
        user_name = interaction.user.display_name
        sh = get_sheet()
        resp_sheet = get_or_create_responses_tab(sh)
        records = resp_sheet.get_all_records()

        updated = False
        for idx, row in enumerate(records, start=2):
            if str(row["Player"]) == user_name:
                resp_sheet.update_cell(idx, 2, "Any")
                resp_sheet.update_cell(idx, 3, "")
                resp_sheet.update_cell(idx, 4, "")
                resp_sheet.update_cell(idx, 5, "TRUE")
                resp_sheet.update_cell(idx, 6, "Pending")
                updated = True
                break

        if not updated:
            resp_sheet.append_row([user_name, "Any", "", "", "TRUE", "Pending"])

        log_action(self.comp_name, user_name, "Registered Preference", "Fill / Flex")
        await interaction.response.send_message("Registered you for **Fill / Flex**!", ephemeral=True)

# --- UI Components for Callers (!comp) ---

class ShotcallerModal(ui.Modal, title="Assign Shotcaller"):
    shotcaller_input = ui.TextInput(
        label="Shotcaller Name (Optional)",
        placeholder="Type player name here, or leave blank...",
        required=False,
        max_length=50
    )

    def __init__(self, selected_tab):
        super().__init__()
        self.selected_tab = selected_tab

    async def on_submit(self, interaction: discord.Interaction):
        global LAST_ANNOUNCED_TAB
        LAST_ANNOUNCED_TAB = self.selected_tab
        shotcaller_name = self.shotcaller_input.value.strip()

        sc_assigned = False
        if shotcaller_name:
            sc_assigned = assign_shotcaller_in_sheet(self.selected_tab, shotcaller_name)

        description_text = "📝 **Preference Phase Open**: Click **Submit Preferences** to pick your role choices from dropdowns, or select **Fill**."
        if sc_assigned:
            description_text = f"👑 **Shotcaller**: **{shotcaller_name}**\n\n" + description_text

        embed = discord.Embed(
            title=f"⚔️ Albion Online Active Comp: {self.selected_tab}",
            description=description_text,
            color=discord.Color.gold()
        )

        view = MultiPrefView(self.selected_tab)

        await interaction.channel.send(
            content=f"📢 **Sign-ups Open for {self.selected_tab}!** @here",
            embed=embed,
            view=view
        )

        success_msg = f"✅ Launched signup for **{self.selected_tab}**!"
        if sc_assigned:
            success_msg += f" (Assigned Shotcaller: **{shotcaller_name}**)"
        elif shotcaller_name and not sc_assigned:
            success_msg += f"\n⚠️ Could not find a row named `Shotcaller` in `{self.selected_tab}` sheet."

        await interaction.response.send_message(success_msg, ephemeral=True)

class CompSelect(ui.Select):
    def __init__(self, tab_names):
        options = [
            discord.SelectOption(label=tab, description=f"Load sign-up for {tab}", value=tab)
            for tab in tab_names[:25]
        ]
        super().__init__(
            placeholder="Select a comp layout to launch...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_tab = self.values[0]
        # Launch modal to prompt for Shotcaller name
        modal = ShotcallerModal(selected_tab)
        await interaction.response.send_modal(modal)

class CompSelectView(ui.View):
    def __init__(self, tab_names):
        super().__init__(timeout=60)
        self.add_item(CompSelect(tab_names))

# --- Handout Core Logic Functions ---

async def execute_handout_process(channel, target_tab):
    """Core multi-pass handout logic with duplicate assignment prevention."""
    sh = get_sheet()
    try:
        active_sheet = sh.worksheet(target_tab)
        resp_sheet = get_or_create_responses_tab(sh)
    except Exception as e:
        await channel.send(f"Error loading sheets for `{target_tab}`: {e}")
        return

    comp_records = active_sheet.get_all_records()
    all_responses = resp_sheet.get_all_records()

    unprocessed_responses = []
    for idx, resp in enumerate(all_responses, start=2):
        if str(resp.get("Status", "")).strip().lower() != "processed":
            resp["_row_idx"] = idx
            unprocessed_responses.append(resp)

    if not unprocessed_responses:
        await channel.send("No new/pending responses found to distribute!")
        return

    # Track players who already have a slot (including pre-assigned ones)
    assigned_players = set()

    open_slots = {}
    for idx, row in enumerate(comp_records, start=2):
        existing_player = str(row.get("Signed Up", "")).strip()
        if existing_player:
            assigned_players.add(existing_player.lower())
        else:
            weapon = str(row["Role / Weapon"]).strip().lower()
            if weapon not in open_slots:
                open_slots[weapon] = []
            open_slots[weapon].append((idx, row["Role / Weapon"]))

    unassigned = []
    fill_players = []
    assigned_log = []
    processed_rows = []

    candidates = []
    for resp in unprocessed_responses:
        if str(resp.get("Is Fill", "")).upper() == "TRUE":
            fill_players.append(resp)
        else:
            candidates.append(resp)

    def try_assign(resp, pref_str):
        if not pref_str:
            return False
        
        player = resp["Player"]
        player_key = player.lower()

        # Prevent duplicate assignment across slots
        if player_key in assigned_players:
            return False

        key = pref_str.strip().lower()
        if key in open_slots and len(open_slots[key]) > 0:
            target_row, official_weapon = open_slots[key].pop(0)
            active_sheet.update_cell(target_row, 3, player)
            assigned_log.append(f"• **{player}** → {official_weapon}")
            processed_rows.append(resp["_row_idx"])
            assigned_players.add(player_key)
            log_action(target_tab, player, "Role Handout", f"Assigned to {official_weapon} (Row {target_row})")
            return True
        return False

    # Pass 1: Primary
    remaining_p2 = []
    for resp in candidates:
        if not try_assign(resp, resp.get("Primary Preference")):
            remaining_p2.append(resp)

    # Pass 2: Secondary
    remaining_p3 = []
    for resp in remaining_p2:
        if not try_assign(resp, resp.get("Secondary Preference")):
            remaining_p3.append(resp)

    # Pass 3: Tertiary
    for resp in remaining_p3:
        if not try_assign(resp, resp.get("Tertiary Preference")):
            if resp["Player"].lower() not in assigned_players:
                unassigned.append(resp["Player"])

    # Append Fill players to Column E
    fill_names = []
    if fill_players:
        existing_fills = active_sheet.col_values(5)[1:]
        start_row = len(existing_fills) + 2
        
        valid_fills = [f for f in fill_players if f["Player"].lower() not in assigned_players]
        if valid_fills:
            fill_names = [f["Player"] for f in valid_fills]
            fill_data = [[p] for p in fill_names]
            active_sheet.update(f"E{start_row}:E{start_row + len(valid_fills) - 1}", fill_data)
            for f in valid_fills:
                processed_rows.append(f["_row_idx"])
                assigned_players.add(f["Player"].lower())

    # Mark assigned & fill players as Processed in the Responses sheet
    for row_idx in processed_rows:
        resp_sheet.update_cell(row_idx, 6, "Processed")

    embed = discord.Embed(
        title=f"✅ Handout Complete: {target_tab}",
        color=discord.Color.green()
    )
    embed.add_field(
        name=f"Newly Assigned Players ({len(assigned_log)})",
        value="\n".join(assigned_log) if assigned_log else "No new roles assigned.",
        inline=False
    )
    if fill_names:
        embed.add_field(name="Fill / Flex Added", value=", ".join(fill_names), inline=False)
    if unassigned:
        embed.add_field(name="⚠️ Unassigned (Slots Full / Remained Pending)", value=", ".join(unassigned), inline=False)

    await channel.send(embed=embed)

class HandoutConfirmView(ui.View):
    def __init__(self, target_tab, author):
        super().__init__(timeout=60)
        self.target_tab = target_tab
        self.author = author

    @ui.button(label="Confirm Handout", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm_handout(self, interaction: discord.Interaction, button: ui.Button):
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(
            content=f"⏳ **Executing role handout for `{self.target_tab}`...**", 
            view=self
        )
        
        await execute_handout_process(interaction.channel, self.target_tab)

    @ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_handout(self, interaction: discord.Interaction, button: ui.Button):
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=f"❌ **Handout cancelled for `{self.target_tab}`.** Responses remain untouched.", 
            view=self
        )

async def request_handout_confirmation(channel, target_tab, author):
    """Checks for pending responses first, then prompts caller for explicit confirmation."""
    sh = get_sheet()
    try:
        resp_sheet = get_or_create_responses_tab(sh)
        responses = resp_sheet.get_all_records()
    except Exception as e:
        await channel.send(f"Error checking sheets: {e}")
        return

    pending_responses = [r for r in responses if str(r.get("Status", "")).strip().lower() != "processed"]

    if not pending_responses:
        await channel.send(f"⚠️ No pending responses found for **{target_tab}**! All responses have already been handed out.")
        return

    count = len(pending_responses)
    confirm_view = HandoutConfirmView(target_tab, author)
    
    await channel.send(
        content=(
            f"⚠️ **HANDOUT CONFIRMATION**: You are about to process **{count} pending response(s)** for **`{target_tab}`**.\n"
            f"Assigned players will be marked as `Processed` and assigned roles in the comp tab.\n\n"
            f"Are you sure you want to proceed?"
        ),
        view=confirm_view
    )

# --- UI Components for Handout Selection (!handout) ---

class HandoutSelect(ui.Select):
    def __init__(self, tab_names, default_tab=None):
        options = [
            discord.SelectOption(
                label=tab, 
                description=f"Select {tab} for handout", 
                value=tab,
                default=(tab == default_tab)
            )
            for tab in tab_names[:25]
        ]
        super().__init__(
            placeholder="Select a comp tab...",
            min_values=1,
            max_values=1,
            options=options,
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_tab = self.values[0]
        await interaction.response.defer()

class HandoutSelectView(ui.View):
    def __init__(self, tab_names, default_tab=None):
        super().__init__(timeout=60)
        self.selected_tab = default_tab or tab_names[0]
        self.add_item(HandoutSelect(tab_names, default_tab=self.selected_tab))

    @ui.button(label="Run Handout", style=discord.ButtonStyle.primary, emoji="🚀", row=1)
    async def confirm_selection(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        
        await request_handout_confirmation(interaction.channel, self.selected_tab, interaction.user)

# --- Commands ---

@bot.command(name="comp")
@commands.has_role(REQUIRED_ROLE)
async def show_comp(ctx, target_tab: str = None):
    """Opens a dropdown menu for Callers to pick an active comp tab."""
    sh = get_sheet()

    ignored_tabs = {"Responses", "Audit Log"}
    all_worksheets = sh.worksheets()
    available_tabs = [ws.title for ws in all_worksheets if ws.title not in ignored_tabs]

    if not available_tabs:
        await ctx.send("❌ No valid comp tabs found in the spreadsheet!")
        return

    if target_tab:
        matching_tab = next((t for t in available_tabs if t.lower() == target_tab.lower()), None)
        if matching_tab:
            # Send prompt directly if tab was specified in arguments
            modal = ShotcallerModal(matching_tab)
            await ctx.send(content=f"🎯 Launching comp `{matching_tab}`. Select option below:")
            return
        else:
            await ctx.send(f"⚠️ Tab `{target_tab}` not found. Please choose from available comps below:")

    view = CompSelectView(available_tabs)
    await ctx.send(
        content="🎯 **Select which Comp layout you want to open for sign-ups:**",
        view=view
    )

@bot.command(name="handout")
@commands.has_role(REQUIRED_ROLE)
async def perform_handout(ctx, target_tab: str = None):
    """Prompts for target tab & confirmation before running role distribution."""
    global LAST_ANNOUNCED_TAB

    if target_tab:
        await request_handout_confirmation(ctx.channel, target_tab, ctx.author)
        return

    sh = get_sheet()
    ignored_tabs = {"Responses", "Audit Log"}
    all_worksheets = sh.worksheets()
    available_tabs = [ws.title for ws in all_worksheets if ws.title not in ignored_tabs]

    if not available_tabs:
        await ctx.send("❌ No valid comp tabs found in the spreadsheet!")
        return

    default_selection = LAST_ANNOUNCED_TAB if LAST_ANNOUNCED_TAB in available_tabs else available_tabs[0]

    view = HandoutSelectView(available_tabs, default_tab=default_selection)
    
    notice = f" Auto-detected last announced comp: **{LAST_ANNOUNCED_TAB}**" if LAST_ANNOUNCED_TAB else ""
    await ctx.send(
        content=f"🎯 **Select which Comp layout to run handout for:**{notice}",
        view=view
    )

@bot.command(name="reset")
@commands.has_role(REQUIRED_ROLE)
async def reset_comp(ctx, target_tab: str = None):
    """Clears player assignments in a specified comp tab and flushes Responses."""
    sh = get_sheet()
    ignored_tabs = {"Responses", "Audit Log"}
    all_worksheets = sh.worksheets()
    available_tabs = [ws.title for ws in all_worksheets if ws.title not in ignored_tabs]

    if not available_tabs:
        await ctx.send("❌ No valid comp tabs found in the spreadsheet!")
        return

    selected_tab = target_tab or (LAST_ANNOUNCED_TAB if LAST_ANNOUNCED_TAB in available_tabs else available_tabs[0])

    try:
        sheet = sh.worksheet(selected_tab)
        resp_sheet = get_or_create_responses_tab(sh)
    except Exception as e:
        await ctx.send(f"❌ Error loading sheet `{selected_tab}`: {e}")
        return

    records = sheet.get_all_records()
    for idx in range(2, len(records) + 2):
        sheet.update_cell(idx, 3, "")

    sheet.batch_clear(["E2:E100"])
    resp_sheet.batch_clear(["A2:F1000"])

    log_action(selected_tab, ctx.author.display_name, "Reset Comp", "Cleared slots and responses")
    await ctx.send(f"✅ Reset all signups and responses for: **{sheet.title}**")

@show_comp.error
@perform_handout.error
@reset_comp.error
async def role_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send(f"❌ You need the **{REQUIRED_ROLE}** role to use this command.")

# --- Start Bot ---
bot.run(DISCORD_TOKEN)