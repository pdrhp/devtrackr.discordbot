import discord
from discord import ui
from datetime import datetime, timedelta
from typing import Optional

from src.utils.config import get_br_time, BRAZIL_TIMEZONE, log_command
from src.storage.daily import submit_daily_update

class DailyUpdateModal(ui.Modal, title="Atualização Diária"):
    """Modal para input de atualização diária."""

    daily_content = ui.TextInput(
        label="O que você fez?",
        style=discord.TextStyle.paragraph,
        placeholder="Descreva o que você fez no dia anterior...",
        required=True,
        min_length=10,
        max_length=1000
    )

    def __init__(self, report_date: Optional[str] = None, user: discord.User = None):
        super().__init__()
        self.report_date = report_date
        self.user = user

        if report_date:
            date_obj = datetime.strptime(report_date, "%Y-%m-%d")
            date_obj = date_obj.replace(tzinfo=BRAZIL_TIMEZONE)
            date_formatted = date_obj.strftime("%d/%m/%Y")
            self.daily_content.placeholder = f"Descreva o que você fez em {date_formatted}..."

    async def on_submit(self, interaction: discord.Interaction):
        """Chamado quando o usuário envia o formulário."""
        user_id = str(interaction.user.id)
        content = self.daily_content.value

        success, message = submit_daily_update(user_id, content, self.report_date)

        if success:
            if self.report_date:
                date_obj = datetime.strptime(self.report_date, "%Y-%m-%d")
                date_obj = date_obj.replace(tzinfo=BRAZIL_TIMEZONE)
                date_formatted = date_obj.strftime("%d/%m/%Y")
                date_display = f"**{date_formatted}**"
                report_date_log = date_formatted
            else:
                yesterday = get_br_time() - timedelta(days=1)
                date_display = f"**{yesterday.strftime('%d/%m/%Y')}**"
                report_date_log = yesterday.strftime('%d/%m/%Y')

            embed = discord.Embed(
                title="📝 Nova Atualização Diária",
                description=f"**{interaction.user.display_name}** enviou uma atualização para {date_display}",
                color=discord.Color.green()
            )

            embed.add_field(
                name="Conteúdo",
                value=content,
                inline=False
            )

            current_time_br = get_br_time().strftime("%d/%m/%Y %H:%M:%S")
            embed.set_footer(text=f"Horário de Brasília: {current_time_br}")

            await interaction.response.send_message(embed=embed, ephemeral=False)

            log_command("DAILY UPDATE", interaction.user, "/daily",
                       f"Atualização para {report_date_log} registrada com sucesso ({len(content)} caracteres)")
        else:
            await interaction.response.send_message(
                f"⚠️ {message}",
                ephemeral=True
            )

            log_command("ERRO", interaction.user, "/daily", f"Erro: {message}")