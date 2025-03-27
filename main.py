import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.realpath(__file__)))

from src.bot.bot import run_bot

if __name__ == "__main__":
    run_bot()