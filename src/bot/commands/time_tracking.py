"""
Módulo de comandos de rastreamento de tempo para o Team Analysis Discord Bot.
"""

from typing import Optional
import logging

import discord
from discord import app_commands
from discord.ext import commands

from src.storage.feature_toggle import is_feature_enabled
from src.storage.time_tracking import clock_in, clock_out
from src.utils.config import get_env, get_br_time, log_command, TIME_TRACKING_CHANNEL_ID

logger = logging.getLogger('team_analysis_bot')


class TimeTrackingCommands(commands.Cog):
    """Comandos relacionados ao controle de horas/ponto."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def handle_disabled_feature(self, interaction: discord.Interaction):
        """Trata interação quando a funcionalidade de controle de horas está desativada."""
        await interaction.response.send_message(
            "⚠️ O sistema de ponto está desativado no momento. "
            "Um administrador pode ativá-lo com o comando `/toggle funcionalidade=ponto`.",
            ephemeral=True
        )
        log_command("FEATURE DESATIVADA", interaction.user, "/on ou /off", "Sistema de ponto desativado")

    async def check_channel(self, interaction: discord.Interaction):
        """Verifica se o comando está sendo usado no canal correto."""
        time_tracking_channel_id = get_env(TIME_TRACKING_CHANNEL_ID, "0")

        if time_tracking_channel_id == "0":
            return True

        if interaction.channel_id != int(time_tracking_channel_id):
            try:
                time_channel = await self.bot.fetch_channel(int(time_tracking_channel_id))
                await interaction.response.send_message(
                    f"⚠️ Por favor, use os comandos de controle de ponto no canal {time_channel.mention}.",
                    ephemeral=True
                )
                log_command("ERRO", interaction.user, f"/{interaction.command.name}",
                          f"Canal incorreto. Usou no canal #{interaction.channel.name} mas deveria ser #{time_channel.name}")
                return False
            except (discord.NotFound, discord.Forbidden, ValueError):
                return True

        return True

    @app_commands.command(name="on", description="Registra entrada e inicia contagem de horas")
    @app_commands.describe(observacao="Observação opcional sobre este registro de entrada")
    async def clock_in(self, interaction: discord.Interaction, observacao: Optional[str] = None):
        """Comando de registro de entrada."""
        if not is_feature_enabled("ponto"):
            await self.handle_disabled_feature(interaction)
            return

        if not await self.check_channel(interaction):
            return

        user_id = str(interaction.user.id)
        success, message = clock_in(user_id, observacao)

        if success:
            timestamp = discord.utils.format_dt(discord.utils.utcnow(), style='F')
            br_time = get_br_time().strftime("%d/%m/%Y %H:%M:%S")

            message_content = [
                f"🕒 **{interaction.user.display_name}** registrou ponto com sucesso!",
                f"**Entrada:** {timestamp}",
                f"**Horário de Brasília:** {br_time}"
            ]

            if observacao:
                message_content.append(f"**Observação:** {observacao}")

            await interaction.response.send_message(
                "\n".join(message_content),
                ephemeral=False
            )

            log_details = f"Entrada registrada às {br_time}"
            if observacao:
                log_details += f" | Observação: {observacao}"

            log_command("ENTRADA", interaction.user, "/on", log_details)
        else:
            await interaction.response.send_message(
                f"⚠️ {message}",
                ephemeral=True
            )

            log_command("ERRO", interaction.user, "/on", f"Erro: {message}")

    @app_commands.command(name="off", description="Registra saída e para contagem de horas")
    @app_commands.describe(observacao="Observação opcional sobre este registro de saída")
    async def clock_out(self, interaction: discord.Interaction, observacao: Optional[str] = None):
        """Comando de registro de saída."""
        if not is_feature_enabled("ponto"):
            await self.handle_disabled_feature(interaction)
            return

        if not await self.check_channel(interaction):
            return

        user_id = str(interaction.user.id)
        success, message, duration = clock_out(user_id, observacao)

        if success:
            timestamp = discord.utils.format_dt(discord.utils.utcnow(), style='F')
            br_time = get_br_time().strftime("%d/%m/%Y %H:%M:%S")

            message_content = [
                f"🕒 **{interaction.user.display_name}** registrou ponto com sucesso!",
                f"**Saída:** {timestamp}",
                f"**Horário de Brasília:** {br_time}",
                f"**Tempo trabalhado:** {duration}"
            ]

            if observacao:
                message_content.append(f"**Observação:** {observacao}")

            await interaction.response.send_message(
                "\n".join(message_content),
                ephemeral=False
            )

            log_details = f"Saída registrada às {br_time}, duração: {duration}"
            if observacao:
                log_details += f" | Observação: {observacao}"

            log_command("SAÍDA", interaction.user, "/off", log_details)
        else:
            await interaction.response.send_message(
                f"⚠️ {message}",
                ephemeral=True
            )

            log_command("ERRO", interaction.user, "/off", f"Erro: {message}")