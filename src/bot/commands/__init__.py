"""
Pacote de comandos para o Team Analysis Discord Bot.
"""

import logging
from discord.ext import commands

from src.bot.commands.support import SupportCommands
from src.bot.commands.user import UserCommands
from src.bot.commands.admin import AdminCommands
from src.bot.commands.time_tracking import TimeTrackingCommands
from src.bot.commands.daily import DailyCommands

logger = logging.getLogger('team_analysis_bot')

__all__ = [
    'SupportCommands',
    'UserCommands',
    'AdminCommands',
    'TimeTrackingCommands',
    'DailyCommands',
    'setup',
]

async def setup(bot: commands.Bot):
    """Configura todos os cogs de comandos."""
    logger.info("Carregando cogs de comandos...")

    await bot.add_cog(AdminCommands(bot))
    await bot.add_cog(TimeTrackingCommands(bot))
    await bot.add_cog(UserCommands(bot))
    await bot.add_cog(DailyCommands(bot))
    await bot.add_cog(SupportCommands(bot))

    logger.info("Todos os cogs de comandos foram carregados com sucesso!")
