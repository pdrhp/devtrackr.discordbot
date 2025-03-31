import discord
from discord import ui
from typing import Optional

from src.utils.config import log_command
from src.bot.modals import DailyUpdateModal

class DailyUpdateView(ui.View):
    """View com botões para atualizar ou cancelar uma atualização diária existente."""

    def __init__(self, user: discord.User, report_date: Optional[str] = None):
        super().__init__(timeout=300)
        self.user = user
        self.report_date = report_date

    @ui.button(label="Atualizar", style=discord.ButtonStyle.primary, emoji="📝")
    async def update_button(self, interaction: discord.Interaction, button: ui.Button):
        """Botão para atualizar uma daily já existente."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "Você não pode interagir com estes botões, pois não são destinados a você.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(DailyUpdateModal(self.report_date, self.user))
        log_command("DAILY UPDATE", interaction.user, f"/daily{f' data={self.report_date}' if self.report_date else ''}", "Modal aberto para atualização")

    @ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        """Botão para cancelar a atualização."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "Você não pode interagir com estes botões, pois não são destinados a você.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="Atualização cancelada.",
            view=None
        )
        log_command("DAILY UPDATE", interaction.user, f"/daily{f' data={self.report_date}' if self.report_date else ''}", "Atualização cancelada pelo usuário")