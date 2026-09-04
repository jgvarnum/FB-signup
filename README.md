# 🤖 Free Beer's Discord Signup Project

A feature-rich Discord bot built with Python, `discord.py`, and asynchronous components.

---

## 📋 Table of Contents
- [Prerequisites](#-prerequisites)
- [Installation & Setup](#-installation--setup)
- [Environment Variables](#-environment-variables)
- [Running the Bot](#-running-the-bot)
- [Bot Usage & Commands](#-bot-usage--commands)
- [Project Structure](#-project-structure)

---

## 🛠️ Prerequisites

Ensure you have the following installed before getting started:
* **Python**: `v3.10` or higher
* **Git**: Installed on your system
* **Discord Developer Account**: Required to register and host a bot application

---

## 📦 Installation & Setup

<Sequence>
  <Step title="Clone the Repository" subtitle="Download the source code locally">
    ```bash
    git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
    cd your-repo-name
    ```
  </Step>

  <Step title="Create a Virtual Environment" subtitle="Isolate dependencies from system Python">
    * **Linux / macOS:**
      ```bash
      python3 -m venv venv
      source venv/bin/activate
      ```
    * **Windows (Command Prompt):**
      ```cmd
      python -m venv venv
      venv\Scripts\activate.bat
      ```
    * **Windows (PowerShell):**
      ```powershell
      python -m venv venv
      .\venv\Scripts\Activate.ps1
      ```
  </Step>

  <Step title="Install Dependencies" subtitle="Fetch required Python libraries">
    Install the base requirements using `pip`:
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```
  </Step>

  <Step title="Configure Environment Variables" subtitle="Store sensitive tokens securely">
    Copy the example environment file and update it with your credentials:
    ```bash
    cp .env.example .env
    ```
  </Step>
</Sequence>

---

## ⚙️ Environment Variables

Open your `.env` file and populate the necessary keys:

| Key | Description | Required | Example |
| :--- | :--- | :---: | :--- |
| `DISCORD_TOKEN` | Bot authentication token from Discord Developer Portal | **Yes** | `MTI3...` |
| `GUILD_ID` | Specific server ID for instant slash command registration (testing) | Optional | `123456789012345678` |
| `COMMAND_PREFIX` | Prefix used for traditional text commands | Optional | `!` |

---

## 🚀 Running the Bot

1. Ensure your virtual environment is active (`(venv)` should appear in your terminal prompt).
2. Start the main bot file:
   ```bash
   python main.py