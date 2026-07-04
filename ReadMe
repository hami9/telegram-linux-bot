# 🐧 Telegram Linux Terminal Bot

A feature-rich Telegram group and channel management bot designed to mimic a Linux Command Line Interface (CLI), built with Python, Pyrogram, and powered by the advanced **Gemini 2.5 Flash AI Core**. 

Manage your communities, trigger administrative system commands, and chat with an embedded terminal AI assistant—all natively through Telegram.

---

## 🚀 Features

*   **⚡ Automated Privilege Detection (`whoami`):** Dynamically parses Telegram API user states to assign `root` (Owner), `sudoers` (Admins), or standard `user` permissions automatically.
*   **🧠 Gemini AI Terminal Core (`/ai`, `/gemini`):** Direct pipeline to Google's Gemini API, tailored to respond with a witty, technical Linux-themed persona wrapped in code blocks.
*   **👥 Package Mentions (`alias`):** Custom indexing to simulate terminal aliases. Group members together (e.g., `devs`, `mods`) and notify them instantly.
*   **🧹 Terminal Housekeeping (`clear --terminal`):** Instantly deletes command execution logs from the chat window to maintain clean system outputs.
*   **🔒 Process Purging (`sudo userdel -f`):** Kick or ban malicious threads (users) from the server via direct text arguments or message replies.

---

## 💻 Command Reference

| Linux CLI Simulation | Telegram Bot Action | Permission Level |
| :--- | :--- | :--- |
| `whoami` | Displays user identity, chat ID, and system privilege. | All Users |
| `/ai <prompt>` | Queries the integrated Gemini AI terminal core. | All Users |
| `alias add <name> <@m1>` | Maps multiple user handles to a single alias package. | Sudoers / Root |
| `alias run <name>` | Pings/mentions all users assigned to the specified alias. | All Users |
| `sudo userdel -f @user` | Safely drops/bans a user from the chat framework. | Sudoers / Root |
| `clear --terminal` | Purges command messages to clear chat congestion. | Sudoers / Root |

---

## ⚙️ Installation & Deployment

### 1. Clone the Repository
```bash
git clone [https://github.com/hami9/hami.git](https://github.com/hami9/hami.git)
cd hami
