**Set up**
**After pulling the files**
create a Python virtual environment called .venv
*run in terminal:*

python -m venv .venv

*Activiate it:*
.\.vemv\scripts\Activate.ps1

You should see a .venv file in your terminal

**Install Dependacies**
*Get the python packages*

python -m pip install -r requirements.txt

**Create the .env file for the API Key**
*Put the API from the discord into this file*
Do not commit or upload .env to github as it will flag it for sensitive infomation

GENAI_API_KEY=api_key_from_pinned_discord_updates_chat

**GITINGORE file**
create a git ignore file to let github know what to ignore

.gitignore 

contents:
#put your API key in here
.env

#python enironment
.venv/

# python cache
__pycache__/
*.pyc