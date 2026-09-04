# ⚔️ Albion Online Comp Management Bot — Setup Guide

A complete end-to-end setup guide to deploy your own instance of the Albion Online Comp & Handout Management Discord Bot. This bot automates player sign-ups, preference collecting, Shotcaller assignments, multi-pass role distribution, and audit logging using Discord and Google Sheets.

---

## 📋 Table of Contents
- [Prerequisites](#-prerequisites)
- [Step 1: Discord Developer Portal Setup](#step-1-discord-developer-portal-setup)
- [Step 2: Google Cloud Platform & Sheets API Setup](#step-2-google-cloud-platform--sheets-api-setup)
- [Step 3: Google Sheets Spreadsheet Configuration](#step-3-google-sheets-spreadsheet-configuration)
- [Step 4: Bot Code & Dependency Setup](#step-4-bot-code--dependency-setup)
- [Step 5: Running the Bot](#step-5-running-the-bot)
- [Step 6: User Guide & Bot Usage](#step-6-user-guide--bot-usage)
- [Troubleshooting & FAQs](#-troubleshooting--faqs)

---

## 🛠️ Prerequisites

Before starting, ensure you have:
* **Python**: `v3.10` or higher installed on your computer or hosting server.
* **Discord Account**: Admin permissions on your target Discord server.
* **Google Account**: Access to Google Drive and Google Cloud Console.
* **Text Editor**: VS Code, PyCharm, or any standard text editor.

---

## Step 1: Discord Developer Portal Setup

### 1.1 Create the Discord Application
1. Navigate to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application** in the top-right corner.
3. Enter a name (e.g., `Albion Comp Bot`) and click **Create**.

### 1.2 Configure Bot & Retrieve Token
1. Select **Bot** from the left-hand menu.
2. Click **Reset Token** to generate your bot token. Copy this string and keep it safe — you will need it later for your `.env` file.
3. Scroll down to **Privileged Gateway Intents** and enable:
   * **Message Content Intent** (Required to read `!` prefixed commands).
   * **Server Members Intent** (Recommended).
4. Click **Save Changes**.

### 1.3 Invite Bot to Your Discord Server
1. Select **OAuth2 > URL Generator** from the left menu.
2. Under **Scopes**, check `bot`.
3. Under **Bot Permissions**, select:
   * `Send Messages`
   * `Embed Links`
   * `Read Message History`
   * `Use External Emojis`
4. Copy the generated **URL** at the bottom of the page, paste it into your browser, select your server, and click **Authorize**.

---

## Step 2: Google Cloud Platform & Sheets API Setup

### 2.1 Create GCP Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown in the top bar and select **New Project**.
3. Name it `Albion-Comp-Bot` and click **Create**.

### 2.2 Enable Required Google APIs
1. Navigate to **APIs & Services > Library**.
2. Search for **Google Sheets API**, click on it, and click **Enable**.
3. Return to the Library, search for **Google Drive API**, click on it, and click **Enable**.

### 2.3 Generate Service Account Key
1. Go to **APIs & Services > Credentials**.
2. Click **+ Create Credentials** at the top and select **Service Account**.
3. Enter a name (e.g., `comp-bot-service-account`) and click **Create and Continue**, then click **Done**.
4. Click on the newly created service account email under the **Service Accounts** list.
5. Navigate to the **Keys** tab, click **Add Key > Create new key**, select **JSON**, and click **Create**.
6. Save the downloaded JSON file. Rename this file to `credentials.json`.

## Step 3: Google Sheets Spreadsheet Configuration

### 3.1 Create and Name Spreadsheet
1. Go to [Google Sheets](https://sheets.google.com) and create a new blank spreadsheet.
2. Title the spreadsheet **`Free Beer Comps`** (or adjust `SHEET_NAME` in `main.py` if using a different title).

### 3.2 Configure Comp Layout Tabs
Create tabs for each of your guild's ZvZ/party compositions (e.g., `Brawl Comp`, `Clap Comp`). Configure each comp sheet with the following exact column headers in **Row 1**:

| Column A | Column B | Column C | Column D | Column E |
| :--- | :--- | :--- | :--- | :--- |
| **Party** | **Role / Weapon** | **Signed Up** | *(Optional)* | **Fill / Flex** |

* **Row 2 onward in Column B**: List the weapon/role names available (e.g., `Shotcaller`, `1H Mace`, `Brimstone`, `Fallen Staff`).
* **Column C (`Signed Up`)**: Leave blank for available slots.

### 3.3 Share Spreadsheet with Service Account
1. Open your downloaded `credentials.json` file in a text editor.
2. Find the `"client_email"` field (looks like `comp-bot-service-account@your-project.iam.gserviceaccount.com`).
3. In your Google Sheet, click the top-right **Share** button.
4. Paste the service account email, assign **Editor** permissions, uncheck "Notify people", and click **Share**.

---

## Step 4: Bot Code & Dependency Setup

### 4.1 Prepare Directory & Virtual Environment
Open your terminal or command prompt and run:

```bash
# Create and enter project directory
mkdir albion-comp-bot
cd albion-comp-bot

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux / macOS:
source venv/bin/activate
# Windows (Command Prompt):
venv\Scripts\activate.bat
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
```

### 4.2 Install Dependencies
Install the required packages:

```bash
pip install --upgrade pip
pip install discord.py gspread oauth2client python-dotenv
```

### 4.3 Create Project Files
1. Move your credentials.json key file into this root project directory.
2. Create a .env file in the root folder with the following:
```bash
DISCORD_TOKEN=your_copied_discord_bot_token_here
```
3. Save your Python script as main.py in the root folder.

### 4.4 Directory Structure Verification
Your directory structure must look like this:
```bash
albion-comp-bot/
├── venv/
├── .env
├── credentials.json
└── main.py
```

## Step 5: Running the Bot
1. Ensure your virtual environment is active ((venv) shown in terminal)
2. Start the bot:
```bash
python main.py
```
3. In configured correctly, your console will output:
```
Logged in as YourBotName#1234
```
4. On your Discord server, create a role named 'Caller' and assign it to yourself or your group callers (users without this role will not be able to run caller commands).

## Step 6: User Guide & Bot Usage
Workflow Overview
!comp  ──►  Select Comp & Assign Shotcaller  ──►  Players Sign Up  ──►  !handout  ──►  Automated Distribution

1. Open Sign-ups (!comp):
	* Run !comp in a caller channel.
	* Select the comp layout tab from the dropdown.
	* A pop-up modal appears prompting for an optional Shotcaller Name.
	* The bot posts an interactive message with buttons for players to sign up.
2. Distribute Roles (!handout):
	* Once sign-ups are ready, run !handout.
	* Select the target comp tab.
	* The bot verifies pending sign-ups and asks for confirmation.
	* Clicking Confirm Handout runs a multi-pass assignment algorithm (Primary ➔ Secondary ➔ Tertiary preferences), preventing duplicate assignments across multiple open slots and marking assigned entries as Processed in Sheets.
3. Reset Comp (!reset):
	* Run !reset [comp_tab] to clear player assignments in Column C and wipe the Responses tab for the next event
	
## 🛠️ Troubleshooting & FAQs

| Issue | Cause | Solution |
| --- | --- | --- |
| **`MissingRole` Error** | The Discord user running `!comp`, `!handout`, or `!reset` lacks the `Caller` role. | Assign a Discord role named exactly `Caller` to the user. |
| **`APIError: 403` / Sheet Not Found** | The service account email hasn't been shared on Google Sheets. | Open `credentials.json`, copy `client_email`, and grant it **Editor** permissions on Google Sheets. |
| **Dropdown truncated at 25 weapons** | Discord limits UI Select menus to 25 items maximum. | The code automatically truncates weapon dropdown lists to 25 unique items to prevent API crashes. |
| **Primary choice not assigned** | Column header in Sheet does not match exact key string. | Ensure Row 1 of your comp tab has headers **`Role / Weapon`** (Column B) and **`Signed Up`** (Column C). |
