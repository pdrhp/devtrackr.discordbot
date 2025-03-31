import discord
from discord import ui

from src.utils.config import get_br_time, get_env, log_command

class SupportModal(ui.Modal, title="Suporte - Enviar Mensagem"):
    """Modal para envio de mensagens de suporte, erros ou sugestões."""

    support_title = ui.TextInput(
        label="Título",
        style=discord.TextStyle.short,
        placeholder="Ex: Erro ao registrar daily, Sugestão de funcionalidade...",
        required=True,
        min_length=5,
        max_length=100
    )

    support_content = ui.TextInput(
        label="Descrição",
        style=discord.TextStyle.paragraph,
        placeholder="Descreva em detalhes o problema, erro ou sugestão...",
        required=True,
        min_length=10,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        """Chamado quando o usuário envia o formulário."""
        user_id = str(interaction.user.id)
        title = self.support_title.value
        content = self.support_content.value

        support_user_id = get_env("SUPPORT_USER_ID")

        if not support_user_id:
            await interaction.response.send_message(
                "⚠️ O administrador do sistema não configurou um usuário de suporte. Por favor, entre em contato por outros meios.",
                ephemeral=True
            )
            log_command("ERRO", interaction.user, "/suporte", "SUPPORT_USER_ID não configurado")
            return

        try:
            support_user = await interaction.client.fetch_user(int(support_user_id))

            embed = discord.Embed(
                title=f"📩 Nova Mensagem de Suporte: {title}",
                description=f"**Enviado por:** {interaction.user.mention} ({interaction.user.name}, ID: {interaction.user.id})",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="📝 Conteúdo",
                value=content,
                inline=False
            )

            if interaction.guild:
                embed.add_field(
                    name="🏠 Servidor",
                    value=f"{interaction.guild.name} (ID: {interaction.guild.id})",
                    inline=True
                )

            if interaction.channel:
                embed.add_field(
                    name="📢 Canal",
                    value=f"#{interaction.channel.name} (ID: {interaction.channel.id})",
                    inline=True
                )

            current_time_br = get_br_time().strftime("%d/%m/%Y %H:%M:%S")
            embed.set_footer(text=f"Horário de Brasília: {current_time_br}")

            await support_user.send(embed=embed)

            await interaction.response.send_message(
                "✅ Sua mensagem foi enviada com sucesso para o suporte! Obrigado pelo feedback.",
                ephemeral=True
            )

            log_command("SUPORTE", interaction.user, "/suporte", f"Mensagem enviada: {title}")

        except discord.NotFound:
            await interaction.response.send_message(
                "⚠️ Não foi possível encontrar o usuário de suporte. Por favor, informe o administrador do sistema.",
                ephemeral=True
            )
            log_command("ERRO", interaction.user, "/suporte", f"Usuário de suporte não encontrado: {support_user_id}")
        except discord.Forbidden:
            await interaction.response.send_message(
                "⚠️ O bot não tem permissão para enviar mensagens diretas ao usuário de suporte.",
                ephemeral=True
            )
            log_command("ERRO", interaction.user, "/suporte", "Permissão negada para enviar DM ao suporte")
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Ocorreu um erro ao enviar a mensagem: {str(e)}",
                ephemeral=True
            )
            log_command("ERRO", interaction.user, "/suporte", f"Erro ao enviar mensagem: {str(e)}")