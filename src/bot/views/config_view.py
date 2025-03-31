import discord
from discord import ui
from discord.ext import commands
import logging
from datetime import datetime

from src.utils.config import get_br_time, log_command
from src.storage.ignored_dates import get_all_ignored_dates
from src.bot.modals import DateConfigModal

logger = logging.getLogger('team_analysis_bot')

class ConfigView(ui.View):
    """View com botões para escolher configurações do bot."""

    def __init__(self, bot: commands.Bot, funcionalidade: str):
        super().__init__(timeout=300)
        self.bot = bot
        self.funcionalidade = funcionalidade

    @ui.button(label="Configurar Datas Ignoradas", style=discord.ButtonStyle.primary, emoji="📅")
    async def ignored_dates_button(self, interaction: discord.Interaction, button: ui.Button):
        """Botão para configurar datas ignoradas na cobrança de daily."""
        try:
            modal = DateConfigModal(self.bot)
            await interaction.response.send_modal(modal)
            log_command("INFO", interaction.user, f"/config funcionalidade={self.funcionalidade}", "Modal de configuração de datas ignoradas aberto")
        except Exception as e:
            logger.error(f"Erro ao abrir modal de configuração: {str(e)}")
            await interaction.response.send_message(
                f"❌ Ocorreu um erro ao abrir o modal de configuração: {str(e)}",
                ephemeral=True
            )
            log_command("ERRO", interaction.user, f"/config funcionalidade={self.funcionalidade}", f"Erro ao abrir modal: {str(e)}")

    @ui.button(label="Listar Datas Ignoradas", style=discord.ButtonStyle.secondary, emoji="📋")
    async def list_ignored_dates_button(self, interaction: discord.Interaction, button: ui.Button):
        """Botão para listar as datas ignoradas configuradas."""
        ignored_dates = get_all_ignored_dates()

        if not ignored_dates:
            await interaction.response.send_message(
                "📅 Não há datas configuradas para serem ignoradas na cobrança de daily.",
                ephemeral=True
            )
            log_command("INFO", interaction.user, "/config listar-datas", "Nenhuma data configurada")
            return

        embed = discord.Embed(
            title="📅 Datas Ignoradas - Cobrança de Daily",
            description="Estas são as datas configuradas para serem ignoradas na cobrança de daily:",
            color=discord.Color.blue()
        )

        for date_entry in ignored_dates:
            start_date = datetime.strptime(date_entry["start_date"], "%Y-%m-%d")
            end_date = datetime.strptime(date_entry["end_date"], "%Y-%m-%d")
            created_at = datetime.strptime(date_entry["created_at"], "%Y-%m-%d %H:%M:%S")

            start_date_str = start_date.strftime("%d/%m/%Y")
            end_date_str = end_date.strftime("%d/%m/%Y")
            created_at_str = created_at.strftime("%d/%m/%Y %H:%M:%S")

            if start_date == end_date:
                date_desc = f"📆 **{start_date_str}**"
            else:
                date_desc = f"📆 De **{start_date_str}** até **{end_date_str}**"

            try:
                creator_user = await self.bot.fetch_user(int(date_entry["created_by"]))
                creator_name = creator_user.display_name
            except:
                creator_name = f"Usuário {date_entry['created_by']}"

            embed.add_field(
                name=f"ID: {date_entry['id']} - {date_desc}",
                value=f"Configurado por: {creator_name} em {created_at_str}",
                inline=False
            )

        embed.set_footer(text=f"Total: {len(ignored_dates)} configurações • ID pode ser usado com /remover-data-ignorada")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        log_command("CONSULTA", interaction.user, "/config listar-datas", f"Listadas {len(ignored_dates)} configurações")