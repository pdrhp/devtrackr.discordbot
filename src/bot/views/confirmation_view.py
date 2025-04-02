import discord
from discord import ui

from src.utils.config import log_command
from src.storage.daily import clear_all_daily_updates

class ConfirmationView(ui.View):
    """View para confirmação de ações sensíveis, como exclusão de dados."""

    def __init__(self, original_user_id: int):
        super().__init__(timeout=30)
        self.original_user_id = original_user_id

    @ui.button(label="Sim, limpar tudo", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        """Botão de confirmação para limpar todos os dados."""
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("Você não pode confirmar esta ação.", ephemeral=True)
            return

        success, message = clear_all_daily_updates()

        if success:
            result_embed = discord.Embed(
                title="✅ Resumos Diários Limpos",
                description=message,
                color=discord.Color.green()
            )
            log_command("SUCESSO", interaction.user, "/limpar-resumos", message)
        else:
            result_embed = discord.Embed(
                title="❌ Erro ao Limpar Resumos",
                description=message,
                color=discord.Color.red()
            )
            log_command("ERRO", interaction.user, "/limpar-resumos", f"Erro: {message}")

        await interaction.response.edit_message(content=None, embed=result_embed, view=None)
        self.stop()

    @ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        """Botão para cancelar a operação."""
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("Você não pode cancelar esta ação.", ephemeral=True)
            return

        cancel_embed = discord.Embed(
            title="Operação Cancelada",
            description="Nenhuma alteração foi feita.",
            color=discord.Color.blue()
        )

        log_command("CANCELADO", interaction.user, "/limpar-resumos", "Operação cancelada pelo usuário")

        await interaction.response.edit_message(content=None, embed=cancel_embed, view=None)
        self.stop()