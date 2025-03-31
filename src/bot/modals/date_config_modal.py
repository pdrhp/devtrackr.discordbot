import discord
from discord import ui
import logging
from datetime import datetime

from src.utils.config import get_br_time, log_command
from src.storage.ignored_dates import add_ignored_date, get_all_ignored_dates, remove_ignored_date, parse_date_config

logger = logging.getLogger('team_analysis_bot')

class DateConfigModal(ui.Modal, title="Configurar Datas Ignoradas - Cobrança Daily"):
    """Modal para configurar datas ignoradas para cobrança de daily."""

    dates_config = ui.TextInput(
        label="Datas a ignorar",
        style=discord.TextStyle.paragraph,
        placeholder="Formatos: AAAA-MM-DD ou AAAA/MM/DD ou DD/MM/AAAA (data única), AAAA-MM-DD-AAAA-MM-DD (intervalo)",
        required=False
    )

    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        """Processa o envio do modal."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            date_pairs = parse_date_config(self.dates_config.value)

            if not date_pairs:
                await interaction.followup.send(
                    "⚠️ Nenhuma data válida foi configurada. Por favor, verifique o formato e tente novamente.\n\n"
                    "**Formatos aceitos:**\n"
                    "• Data única: `AAAA-MM-DD`, `AAAA/MM/DD` ou `DD/MM/AAAA`\n"
                    "• Intervalo: `AAAA-MM-DD-AAAA-MM-DD`, `AAAA/MM/DD-AAAA/MM/DD` ou `DD/MM/AAAA-DD/MM/AAAA`\n"
                    "• Múltiplas datas: separar por vírgula",
                    ephemeral=True
                )
                log_command("ERRO", interaction.user, "/config daily_collection", "Formato de data inválido")
                return

            existing_dates = get_all_ignored_dates()
            for date_entry in existing_dates:
                remove_ignored_date(date_entry["id"])

            success_count = 0
            for start_date, end_date in date_pairs:
                if add_ignored_date(start_date, end_date, str(interaction.user.id)):
                    success_count += 1

            formatted_dates = []
            for start_date, end_date in date_pairs:
                if start_date == end_date:
                    date_obj = datetime.strptime(start_date, "%Y-%m-%d")
                    formatted_dates.append(f"• {date_obj.strftime('%d/%m/%Y')}")
                else:
                    start_obj = datetime.strptime(start_date, "%Y-%m-%d")
                    end_obj = datetime.strptime(end_date, "%Y-%m-%d")
                    formatted_dates.append(f"• {start_obj.strftime('%d/%m/%Y')} até {end_obj.strftime('%d/%m/%Y')}")

            embed = discord.Embed(
                title="✅ Configuração de Datas Ignoradas",
                description=f"Foram configuradas {success_count} entradas de datas para serem ignoradas na cobrança de daily.",
                color=discord.Color.green()
            )

            if formatted_dates:
                embed.add_field(
                    name="📅 Datas configuradas:",
                    value="\n".join(formatted_dates),
                    inline=False
                )

            embed.set_footer(text=f"Configurado por: {interaction.user.display_name} • {get_br_time().strftime('%d/%m/%Y %H:%M:%S')}")

            await interaction.followup.send(embed=embed, ephemeral=True)
            log_command("INFO", interaction.user, "/config daily_collection", f"Configuradas {success_count} datas ignoradas")

        except Exception as e:
            logger.error(f"Erro ao processar o modal de configuração: {str(e)}")
            await interaction.followup.send(
                f"❌ Ocorreu um erro ao processar a configuração: {str(e)}",
                ephemeral=True
            )
            log_command("ERRO", interaction.user, "/config daily_collection", f"Erro: {str(e)}")