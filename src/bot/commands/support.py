"""
Comandos relacionados ao suporte e feedback.
"""

import discord
from discord import app_commands
from discord.ext import commands

from src.utils.config import log_command
from src.bot.modals import SupportModal

class SupportCommands(commands.Cog):
    """Comandos relacionados ao suporte e feedback."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="suporte", description="Envia uma mensagem de suporte, reporte de erro ou sugestão")
    async def support(self, interaction: discord.Interaction):
        """
        Abre um modal para envio de mensagem de suporte, erro ou sugestão.

        Args:
            interaction: A interação do Discord.
        """
        log_command("COMANDO", interaction.user, "/suporte", "Iniciando modal de suporte")
        await interaction.response.send_modal(SupportModal())
