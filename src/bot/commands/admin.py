import logging
from typing import Dict, List, Optional
import asyncio
from datetime import datetime, timedelta

import discord
from discord import app_commands, ui
from discord.ext import commands

from src.utils.config import get_env, log_command, get_br_time, BRAZIL_TIMEZONE, parse_date_string, format_date_for_display
from src.storage.feature_toggle import is_feature_enabled, toggle_feature
from src.storage.daily import get_missing_updates, clear_all_daily_updates
from src.storage.users import check_user_is_po, register_user as reg_user, remove_user as rem_user, get_user, update_user_nickname
from src.storage.ignored_dates import get_all_ignored_dates, remove_ignored_date, should_ignore_date
from src.bot.views import ConfigView

logger = logging.getLogger('team_analysis_bot')

class AdminCommands(commands.Cog):
    """Cog para comandos administrativos do bot."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _check_daily_collection_enabled(self, interaction: discord.Interaction) -> bool:
        """
        Verifica se as funcionalidades de daily e cobrança estão ativadas.

        Args:
            interaction: Interação do Discord para enviar mensagem de erro.
        """
        if not is_feature_enabled("daily"):
            await interaction.response.send_message(
                "⚠️ A funcionalidade de atualizações diárias está desativada. "
                "Você pode ativá-la com o comando `/toggle funcionalidade=daily`.",
                ephemeral=True
            )
            log_command("INFO", interaction.user, interaction.command.name, "Funcionalidade de daily desativada")
            return False

        if not is_feature_enabled("daily_collection"):
            await interaction.response.send_message(
                "⚠️ A funcionalidade de cobrança de daily está desativada. "
                "Você pode ativá-la com o comando `/toggle funcionalidade=daily_collection`.",
                ephemeral=True
            )
            log_command("INFO", interaction.user, interaction.command.name, "Funcionalidade de cobrança de daily desativada")
            return False

        return True

    async def _process_management_reminder(self, missing_users: List[str], requester: discord.User) -> Dict[str, List[discord.User]]:
        """Processa uma cobrança iniciada pela gerência, enviando mensagens privadas."""
        pending_by_date: Dict[str, List[discord.User]] = {}
        processed_users = []

        if not missing_users:
            return pending_by_date

        for user_id in missing_users:
            try:
                user = await self.bot.fetch_user(int(user_id))
                processed_users.append(user)

                embed = discord.Embed(
                    title="⚠️ Cobrança: Atualizações Diárias Pendentes",
                    description=f"A equipe de gerência de projetos ({requester.mention}) notou que você está com atualizações diárias pendentes.",
                    color=discord.Color.red()
                )

                yesterday = get_br_time() - timedelta(days=1)
                yesterday_db = yesterday.strftime("%Y-%m-%d")

                if yesterday.weekday() >= 5:
                    days_to_subtract = yesterday.weekday() - 4
                    last_weekday = yesterday - timedelta(days=days_to_subtract)
                    yesterday_db = last_weekday.strftime("%Y-%m-%d")

                daily_channel_id = get_env("DAILY_CHANNEL_ID")
                daily_channel = None

                if daily_channel_id:
                    try:
                        daily_channel = await self.bot.fetch_channel(int(daily_channel_id))
                    except (discord.NotFound, discord.Forbidden):
                        pass

                if daily_channel:
                    embed.add_field(
                        name="⏰ Solicitação Urgente",
                        value=f"Por favor, use o comando `/daily` no canal {daily_channel.mention} para atualizar seu status o mais rápido possível.",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="⏰ Solicitação Urgente",
                        value="Por favor, use o comando `/daily` para atualizar seu status o mais rápido possível.",
                        inline=False
                    )

                embed.add_field(
                    name="📝 Lembrete",
                    value="Manter suas atualizações diárias em dia é essencial para o acompanhamento do projeto pela equipe de gerência.",
                    inline=False
                )

                embed.set_footer(text=f"Cobrança realizada em: {get_br_time().strftime('%d/%m/%Y %H:%M:%S')}")

                await user.send(embed=embed)

                if yesterday_db not in pending_by_date:
                    pending_by_date[yesterday_db] = []
                pending_by_date[yesterday_db].append(user)

                logger.info(f"Cobrança gerencial enviada para o usuário {user_id}")
                await asyncio.sleep(1)

            except discord.HTTPException as e:
                logger.error(f"Erro ao enviar cobrança para o usuário {user_id}: {str(e)}")
            except Exception as e:
                logger.error(f"Erro inesperado ao processar cobrança para o usuário {user_id}: {str(e)}")

        return pending_by_date

    @app_commands.command(name="toggle", description="Ativa/desativa funcionalidades do bot")
    @app_commands.describe(funcionalidade="Funcionalidade para ativar/desativar")
    @app_commands.choices(funcionalidade=[
        app_commands.Choice(name="Sistema de daily", value="daily"),
        app_commands.Choice(name="Cobrança de daily", value="daily_collection"),
    ])
    async def toggle_feature(
        self,
        interaction: discord.Interaction,
        funcionalidade: str
    ):
        """
        Ativa ou desativa uma funcionalidade.

        Args:
            interaction: A interação do Discord.
            funcionalidade: A funcionalidade para alternar.
        """
        admin_role_id = int(get_env("ADMIN_ROLE_ID"))
        has_permission = False

        if admin_role_id == 0:
            has_permission = interaction.user.guild_permissions.administrator
        else:
            has_permission = any(role.id == admin_role_id for role in interaction.user.roles)

        if not has_permission:
            await interaction.response.send_message(
                "⚠️ Você não tem permissão para usar este comando.",
                ephemeral=True
            )
            log_command("PERMISSÃO NEGADA", interaction.user, f"/toggle funcionalidade={funcionalidade}")
            return

        was_enabled = is_feature_enabled(funcionalidade)
        new_state = toggle_feature(funcionalidade)

        await interaction.response.send_message(
            f"{'✅' if new_state else '❌'} Funcionalidade **{funcionalidade}** foi {'ativada' if new_state else 'desativada'}.",
            ephemeral=False
        )

        log_command("TOGGLE", interaction.user, f"/toggle funcionalidade={funcionalidade}",
                   f"Alterado de {was_enabled} para {new_state}")

    @app_commands.command(name="limpar-resumos", description="Limpa todos os resumos diários do banco de dados (apenas para testes)")
    async def clear_daily_updates(self, interaction: discord.Interaction):
        """
        Limpa todos os resumos diários do banco de dados.
        Este comando deve ser usado apenas para testes.

        Args:
            interaction: A interação do Discord.
        """
        admin_role_id = int(get_env("ADMIN_ROLE_ID"))
        has_permission = False

        if admin_role_id == 0:
            has_permission = interaction.user.guild_permissions.administrator
        else:
            has_permission = any(role.id == admin_role_id for role in interaction.user.roles)

        if not has_permission:
            await interaction.response.send_message(
                "⚠️ Você não tem permissão para usar este comando. Apenas administradores podem limpar os resumos diários.",
                ephemeral=True
            )
            log_command("PERMISSÃO NEGADA", interaction.user, "/limpar-resumos")
            return

        embed = discord.Embed(
            title="⚠️ Confirmação: Limpar Todos os Resumos",
            description="Esta ação irá remover **PERMANENTEMENTE** todas as atualizações diárias do banco de dados.\n\n**Esta operação não pode ser desfeita.**",
            color=discord.Color.red()
        )

        embed.add_field(
            name="Tem certeza?",
            value="Este comando deve ser usado apenas para fins de teste.",
            inline=False
        )

        log_command("INICIANDO", interaction.user, "/limpar-resumos", "Solicitação de confirmação enviada")

        class ConfirmationView(discord.ui.View):
            def __init__(self, original_user_id: int):
                super().__init__(timeout=30)
                self.original_user_id = original_user_id

            @discord.ui.button(label="Sim, limpar tudo", style=discord.ButtonStyle.danger)
            async def confirm(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
                if btn_interaction.user.id != self.original_user_id:
                    await btn_interaction.response.send_message("Você não pode confirmar esta ação.", ephemeral=True)
                    return

                success, message = clear_all_daily_updates()

                if success:
                    result_embed = discord.Embed(
                        title="✅ Resumos Diários Limpos",
                        description=message,
                        color=discord.Color.green()
                    )
                    log_command("SUCESSO", btn_interaction.user, "/limpar-resumos", message)
                else:
                    result_embed = discord.Embed(
                        title="❌ Erro ao Limpar Resumos",
                        description=message,
                        color=discord.Color.red()
                    )
                    log_command("ERRO", btn_interaction.user, "/limpar-resumos", f"Erro: {message}")

                await btn_interaction.response.edit_message(content=None, embed=result_embed, view=None)
                self.stop()

            @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
            async def cancel(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
                if btn_interaction.user.id != self.original_user_id:
                    await btn_interaction.response.send_message("Você não pode cancelar esta ação.", ephemeral=True)
                    return

                cancel_embed = discord.Embed(
                    title="Operação Cancelada",
                    description="Nenhuma alteração foi feita.",
                    color=discord.Color.blue()
                )

                log_command("CANCELADO", btn_interaction.user, "/limpar-resumos", "Operação cancelada pelo usuário")

                await btn_interaction.response.edit_message(content=None, embed=cancel_embed, view=None)
                self.stop()

        confirmation_view = ConfirmationView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=confirmation_view, ephemeral=True)

    @app_commands.command(name="registrar", description="Registra um usuário no sistema")
    @app_commands.describe(
        tipo="Tipo de usuário (teammember: membro do time, po: product owner)",
        usuario="Usuário para registrar"
    )
    @app_commands.choices(tipo=[
        app_commands.Choice(name="Membro do time", value="teammember"),
        app_commands.Choice(name="Product Owner", value="po")
    ])
    async def register_user(
        self,
        interaction: discord.Interaction,
        tipo: str,
        usuario: discord.User
    ):
        """
        Registra um usuário no sistema.

        Args:
            interaction: A interação do Discord.
            tipo: Tipo de usuário.
            usuario: Usuário a ser registrado.
        """
        admin_role_id = int(get_env("ADMIN_ROLE_ID"))
        has_permission = False

        if admin_role_id == 0:
            has_permission = interaction.user.guild_permissions.administrator
        else:
            has_permission = any(role.id == admin_role_id for role in interaction.user.roles)

        if not has_permission:
            await interaction.response.send_message(
                "⚠️ Você não tem permissão para usar este comando.",
                ephemeral=True
            )
            log_command("PERMISSÃO NEGADA", interaction.user, f"/registrar tipo={tipo} usuario={usuario.name}")
            return

        success, message = reg_user(str(usuario.id), tipo)

        if success:
            await interaction.response.send_message(
                f"✅ {message}",
                ephemeral=False
            )
            log_command("REGISTRO", interaction.user, f"/registrar tipo={tipo} usuario={usuario.name}",
                       f"Usuário registrado com sucesso como {tipo}")
        else:
            await interaction.response.send_message(
                f"⚠️ {message}",
                ephemeral=True
            )
            log_command("ERRO", interaction.user, f"/registrar tipo={tipo} usuario={usuario.name}",
                       f"Erro: {message}")

    @app_commands.command(name="remover", description="Remove um usuário do sistema")
    @app_commands.describe(usuario="Usuário para remover")
    async def remove_user(
        self,
        interaction: discord.Interaction,
        usuario: discord.User
    ):
        """
        Remove um usuário do sistema.

        Args:
            interaction: A interação do Discord.
            usuario: Usuário a ser removido.
        """
        admin_role_id = int(get_env("ADMIN_ROLE_ID"))
        has_permission = False

        if admin_role_id == 0:
            has_permission = interaction.user.guild_permissions.administrator
        else:
            has_permission = any(role.id == admin_role_id for role in interaction.user.roles)

        if not has_permission:
            await interaction.response.send_message(
                "⚠️ Você não tem permissão para usar este comando.",
                ephemeral=True
            )
            log_command("PERMISSÃO NEGADA", interaction.user, f"/remover usuario={usuario.name}")
            return

        success, message = rem_user(str(usuario.id))

        if success:
            await interaction.response.send_message(
                f"✅ {message}",
                ephemeral=False
            )
            log_command("REMOÇÃO", interaction.user, f"/remover usuario={usuario.name}",
                       "Usuário removido com sucesso")
        else:
            await interaction.response.send_message(
                f"⚠️ {message}",
                ephemeral=True
            )
            log_command("ERRO", interaction.user, f"/remover usuario={usuario.name}",
                       f"Erro: {message}")

    @app_commands.command(name="config", description="Configura opções do bot")
    @app_commands.describe(funcionalidade="Funcionalidade a ser configurada")
    @app_commands.choices(funcionalidade=[
        app_commands.Choice(name="Cobrança de Daily", value="daily_collection")
    ])
    async def config(
        self,
        interaction: discord.Interaction,
        funcionalidade: str
    ):
        """
        Configura opções do bot.

        Args:
            interaction: A interação do Discord.
            funcionalidade: A funcionalidade a ser configurada.
        """
        admin_role_id = int(get_env("ADMIN_ROLE_ID"))
        has_permission = False

        if admin_role_id == 0:
            has_permission = interaction.user.guild_permissions.administrator
        else:
            has_permission = any(role.id == admin_role_id for role in interaction.user.roles)

        user = get_user(str(interaction.user.id))
        if user and user['role'] == 'po':
            has_permission = True

        if not has_permission:
            await interaction.response.send_message(
                "⚠️ Você não tem permissão para usar este comando. Apenas administradores e Product Owners podem configurar o bot.",
                ephemeral=True
            )
            log_command("PERMISSÃO NEGADA", interaction.user, f"/config funcionalidade={funcionalidade}")
            return

        if funcionalidade == "daily_collection":
            if not is_feature_enabled("daily"):
                await interaction.response.send_message(
                    "⚠️ A funcionalidade de daily está desativada. "
                    "Você precisa ativá-la primeiro com o comando `/toggle funcionalidade=daily`.",
                    ephemeral=True
                )
                log_command("ERRO", interaction.user, f"/config funcionalidade={funcionalidade}", "Funcionalidade de daily desativada")
                return

            if not is_feature_enabled("daily_collection"):
                await interaction.response.send_message(
                    "⚠️ A funcionalidade de cobrança de daily está desativada. "
                    "Você precisa ativá-la primeiro com o comando `/toggle funcionalidade=daily_collection`.",
                    ephemeral=True
                )
                log_command("ERRO", interaction.user, f"/config funcionalidade={funcionalidade}", "Funcionalidade de cobrança de daily desativada")
                return

            embed = discord.Embed(
                title="⚙️ Configurações - Cobrança de Daily",
                description="Escolha uma das opções abaixo para configurar:",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="📅 Datas Ignoradas",
                value="Configure quais datas devem ser ignoradas na cobrança de daily. "
                      "Útil para feriados, recessos e outros períodos sem trabalho.",
                inline=False
            )

            embed.add_field(
                name="ℹ️ Formatos de Data Aceitos",
                value="• Data única: `2023-12-25`\n"
                      "• Múltiplas datas: `2023-12-25,2023-12-26`\n"
                      "• Intervalo de datas: `2023-12-24-2024-01-03`",
                inline=False
            )

            view = ConfigView(self.bot, funcionalidade)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            log_command("INFO", interaction.user, f"/config funcionalidade={funcionalidade}", "Menu de opções de configuração exibido")
        else:
            await interaction.response.send_message(
                f"⚠️ A funcionalidade '{funcionalidade}' não possui opções de configuração ainda.",
                ephemeral=True
            )
            log_command("ERRO", interaction.user, f"/config funcionalidade={funcionalidade}", "Funcionalidade sem opções de configuração")

    @app_commands.command(name="remover-data-ignorada", description="Remove uma configuração de data ignorada na cobrança de daily")
    @app_commands.describe(
        id="ID da configuração de data a ser removida"
    )
    async def remove_ignored_date(
        self,
        interaction: discord.Interaction,
        id: int
    ):
        """
        Remove uma configuração de data ignorada na cobrança de daily.

        Args:
            interaction: A interação do Discord.
            id: ID da configuração a ser removida.
        """
        admin_role_id = int(get_env("ADMIN_ROLE_ID"))
        has_permission = False

        if admin_role_id == 0:
            has_permission = interaction.user.guild_permissions.administrator
        else:
            has_permission = any(role.id == admin_role_id for role in interaction.user.roles)

        user = get_user(str(interaction.user.id))
        if user and user['role'] == 'po':
            has_permission = True

        if not has_permission:
            await interaction.response.send_message(
                "⚠️ Você não tem permissão para usar este comando. Apenas administradores e Product Owners podem remover datas ignoradas.",
                ephemeral=True
            )
            log_command("PERMISSÃO NEGADA", interaction.user, f"/remover-data-ignorada id={id}")
            return

        if not is_feature_enabled("daily") or not is_feature_enabled("daily_collection"):
            await interaction.response.send_message(
                "⚠️ As funcionalidades de daily ou cobrança de daily estão desativadas.",
                ephemeral=True
            )
            log_command("ERRO", interaction.user, f"/remover-data-ignorada id={id}", "Funcionalidades desativadas")
            return

        ignored_dates = get_all_ignored_dates()
        date_to_remove = None

        for date in ignored_dates:
            if date["id"] == id:
                date_to_remove = date
                break

        if not date_to_remove:
            await interaction.response.send_message(
                f"⚠️ Não foi encontrada configuração de data ignorada com o ID {id}.",
                ephemeral=True
            )
            log_command("ERRO", interaction.user, f"/remover-data-ignorada id={id}", "ID não encontrado")
            return

        if remove_ignored_date(id):
            start_date = datetime.strptime(date_to_remove["start_date"], "%Y-%m-%d")
            end_date = datetime.strptime(date_to_remove["end_date"], "%Y-%m-%d")

            start_date_str = start_date.strftime("%d/%m/%Y")
            end_date_str = end_date.strftime("%d/%m/%Y")

            if start_date == end_date:
                date_desc = f"**{start_date_str}**"
            else:
                date_desc = f"de **{start_date_str}** até **{end_date_str}**"

            await interaction.response.send_message(
                f"✅ Configuração de data ignorada {date_desc} (ID: {id}) foi removida com sucesso.",
                ephemeral=True
            )
            log_command("INFO", interaction.user, f"/remover-data-ignorada id={id}", "Data removida com sucesso")
        else:
            await interaction.response.send_message(
                f"❌ Ocorreu um erro ao tentar remover a configuração de data ignorada com ID {id}.",
                ephemeral=True
            )
            log_command("ERRO", interaction.user, f"/remover-data-ignorada id={id}", "Erro ao remover")

    @app_commands.command(name="listar-datas-ignoradas", description="Lista as datas configuradas para serem ignoradas na cobrança de daily")
    async def list_ignored_dates(self, interaction: discord.Interaction):
        """
        Lista as datas configuradas para serem ignoradas na cobrança de daily.

        Args:
            interaction: A interação do Discord.
        """
        admin_role_id = int(get_env("ADMIN_ROLE_ID"))
        has_permission = False

        if admin_role_id == 0:
            has_permission = interaction.user.guild_permissions.administrator
        else:
            has_permission = any(role.id == admin_role_id for role in interaction.user.roles)

        user = get_user(str(interaction.user.id))
        if user and user['role'] == 'po':
            has_permission = True

        if not has_permission:
            await interaction.response.send_message(
                "⚠️ Você não tem permissão para usar este comando. Apenas administradores e Product Owners podem ver as datas ignoradas.",
                ephemeral=True
            )
            log_command("PERMISSÃO NEGADA", interaction.user, "/listar-datas-ignoradas")
            return

        if not is_feature_enabled("daily") or not is_feature_enabled("daily_collection"):
            await interaction.response.send_message(
                "⚠️ As funcionalidades de daily ou cobrança de daily estão desativadas.",
                ephemeral=True
            )
            log_command("ERRO", interaction.user, "/listar-datas-ignoradas", "Funcionalidades desativadas")
            return

        ignored_dates = get_all_ignored_dates()

        if not ignored_dates:
            await interaction.response.send_message(
                "📅 Não há datas configuradas para serem ignoradas na cobrança de daily.",
                ephemeral=True
            )
            log_command("INFO", interaction.user, "/listar-datas-ignoradas", "Nenhuma data configurada")
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
        log_command("CONSULTA", interaction.user, "/listar-datas-ignoradas", f"Listadas {len(ignored_dates)} configurações")

    @app_commands.command(name="testar-datas-ignoradas", description="Testa se uma data específica está configurada para ser ignorada")
    @app_commands.describe(
        data="Data para testar (formatos aceitos: YYYY-MM-DD, YYYY/MM/DD ou DD/MM/YYYY)"
    )
    async def test_ignored_date(
        self,
        interaction: discord.Interaction,
        data: str
    ):
        """
        Testa se uma data específica está configurada para ser ignorada na cobrança de daily.

        Args:
            interaction: A interação do Discord.
            data: Data para testar.
        """
        admin_role_id = int(get_env("ADMIN_ROLE_ID"))
        has_permission = False

        if admin_role_id == 0:
            has_permission = interaction.user.guild_permissions.administrator
        else:
            has_permission = any(role.id == admin_role_id for role in interaction.user.roles)

        user = get_user(str(interaction.user.id))
        if user and user['role'] == 'po':
            has_permission = True

        if not has_permission:
            await interaction.response.send_message(
                "⚠️ Você não tem permissão para usar este comando.",
                ephemeral=True
            )
            log_command("PERMISSÃO NEGADA", interaction.user, f"/testar-datas-ignoradas data={data}")
            return

        formatted_data = parse_date_string(data)
        if not formatted_data:
            await interaction.response.send_message(
                f"⚠️ Formato de data inválido: {data}. Formatos aceitos: YYYY-MM-DD, YYYY/MM/DD ou DD/MM/YYYY.",
                ephemeral=True
            )
            log_command("ERRO", interaction.user, f"/testar-datas-ignoradas data={data}", "Formato de data inválido")
            return

        try:
            date_obj = datetime.strptime(formatted_data, "%Y-%m-%d")

            is_ignored = should_ignore_date(date_obj)
            formatted_date = format_date_for_display(formatted_data)

            if is_ignored:
                await interaction.response.send_message(
                    f"✅ A data **{formatted_date}** está configurada para ser ignorada na cobrança de daily.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"ℹ️ A data **{formatted_date}** NÃO está configurada para ser ignorada na cobrança de daily.",
                    ephemeral=True
                )

            log_command("INFO", interaction.user, f"/testar-datas-ignoradas data={data}", f"Resultado: {is_ignored}")
        except ValueError:
            await interaction.response.send_message(
                f"⚠️ Erro ao processar a data: {data}.",
                ephemeral=True
            )
            log_command("ERRO", interaction.user, f"/testar-datas-ignoradas data={data}", "Erro ao processar data")

    @app_commands.command(name="cobrar-daily", description="Cobra as atualizações diárias pendentes. (Somente POs e Admins)")
    async def cobrar_daily(self, interaction: discord.Interaction):
        """Comando para POs e admins cobrarem atualizações diárias pendentes."""
        if not await self._check_daily_collection_enabled(interaction):
            return

        br_time = get_br_time()
        is_weekend = br_time.weekday() >= 5

        weekend_notice = ""
        if is_weekend:
            weekend_notice = f"\n\nℹ️ Hoje é fim de semana ({br_time.strftime('%d/%m/%Y')}). O comando verificará apenas atualizações pendentes de dias úteis."

        if should_ignore_date(br_time):
            await interaction.response.send_message(
                f"⚠️ A data atual ({br_time.strftime('%d/%m/%Y')}) está configurada para ser ignorada na cobrança de daily.",
                ephemeral=True
            )
            log_command("INFO", interaction.user, "/cobrar-daily", f"Data {br_time.strftime('%Y-%m-%d')} ignorada")
            return

        daily_channel_id = get_env("DAILY_CHANNEL_ID")

        if daily_channel_id and str(interaction.channel_id) != daily_channel_id:
            try:
                daily_channel = await self.bot.fetch_channel(int(daily_channel_id))
                await interaction.response.send_message(
                    f"Este comando só pode ser usado no canal {daily_channel.mention}.",
                    ephemeral=True
                )
            except (discord.NotFound, discord.Forbidden):
                await interaction.response.send_message(
                    "Este comando só pode ser usado no canal de atualizações diárias.",
                    ephemeral=True
                )
            return

        user_id = str(interaction.user.id)
        admin_role_id = get_env("ADMIN_ROLE_ID")
        has_permission = False

        if check_user_is_po(user_id):
            has_permission = True
            logger.info(f"Usuário {user_id} é PO e solicitou cobrança de atualizações diárias")

        elif admin_role_id and interaction.guild:
            member = interaction.guild.get_member(int(user_id))
            if member and any(role.id == int(admin_role_id) for role in member.roles):
                has_permission = True
                logger.info(f"Usuário {user_id} tem cargo de admin e solicitou cobrança de atualizações diárias")

        if not has_permission:
            await interaction.response.send_message(
                "Você não tem permissão para usar este comando. Somente POs e administradores podem usá-lo.",
                ephemeral=True
            )
            logger.warning(f"Usuário {user_id} tentou usar o comando de cobrança sem permissão")
            return

        await interaction.response.defer(thinking=True)

        missing_users = get_missing_updates()

        if not missing_users:
            await interaction.followup.send(f"Todos os usuários estão com suas atualizações diárias em dia! 🎉{weekend_notice}")
            return

        pending_by_date = await self._process_management_reminder(missing_users, interaction.user)

        if not pending_by_date:
            await interaction.followup.send(f"Não há atualizações pendentes para dias úteis.{weekend_notice}")
            return

        embed = discord.Embed(
            title="📊 Relatório de Cobrança de Atualizações",
            description=f"A equipe de gerência de projetos ({interaction.user.mention}) solicitou uma cobrança das atualizações pendentes.{weekend_notice}",
            color=discord.Color.brand_red()
        )

        for date_str, users in pending_by_date.items():
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            date_obj = date_obj.replace(tzinfo=BRAZIL_TIMEZONE)
            formatted_date = date_obj.strftime("%d/%m/%Y")

            user_list = "\n".join([f"• {user.mention}" for user in users])

            embed.add_field(
                name=f"📅 Dia {formatted_date}",
                value=user_list if user_list else "Nenhum usuário pendente.",
                inline=False
            )

        embed.set_footer(text=f"Cobrança solicitada em: {get_br_time().strftime('%d/%m/%Y %H:%M:%S')}")

        await interaction.followup.send(embed=embed)
        logger.info(f"Cobrança de atualizações diárias executada por {interaction.user.id}")

    @app_commands.command(name="apelidar", description="Define um apelido personalizado para um usuário registrado")
    @app_commands.describe(
        usuario="Usuário que receberá o apelido",
        apelido="Apelido a ser definido para o usuário"
    )
    async def set_nickname(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        apelido: str
    ):
        """
        Define um apelido personalizado para um usuário registrado no sistema.
        Este apelido será usado em relatórios e outras áreas do sistema.

        Args:
            interaction: A interação do Discord.
            usuario: O usuário que receberá o apelido.
            apelido: O apelido a ser definido.
        """
        logger.debug(f"Comando apelidar iniciado para usuário={usuario.id}, apelido='{apelido}'")

        admin_role_id = int(get_env("ADMIN_ROLE_ID"))
        po_role_id = int(get_env("PO_ROLE_ID", "0"))

        has_permission = False

        if interaction.user.guild_permissions.administrator:
            has_permission = True
            logger.debug("Usuário tem permissão de administrador do servidor")

        if admin_role_id != 0 and any(role.id == admin_role_id for role in interaction.user.roles):
            has_permission = True
            logger.debug("Usuário tem o cargo de admin")

        if po_role_id != 0 and any(role.id == po_role_id for role in interaction.user.roles):
            has_permission = True
            logger.debug("Usuário tem o cargo de PO")

        if not has_permission:
            await interaction.response.send_message(
                "⚠️ Você não tem permissão para usar este comando. Apenas administradores e POs podem definir apelidos.",
                ephemeral=True
            )
            log_command("PERMISSÃO NEGADA", interaction.user, f"/apelidar usuario={usuario.id} apelido='{apelido}'")
            logger.warning(f"Permissão negada para {interaction.user.name} (ID: {interaction.user.id}) no comando apelidar")
            return

        target_user = get_user(str(usuario.id))
        if not target_user:
            await interaction.response.send_message(
                "⚠️ Este usuário não está registrado no sistema.",
                ephemeral=True
            )
            log_command("ERRO", interaction.user, f"/apelidar usuario={usuario.id} apelido='{apelido}'", "Usuário não registrado")
            logger.warning(f"Tentativa de definir apelido para usuário não registrado: {usuario.id}")
            return

        success, message = update_user_nickname(str(usuario.id), apelido, str(interaction.user.id))

        if success:
            embed = discord.Embed(
                title="✅ Apelido Definido",
                description=f"O apelido para {usuario.mention} foi definido como **{apelido}**.",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Definido por {interaction.user.display_name}")

            await interaction.response.send_message(embed=embed, ephemeral=True)
            log_command("APELIDO", interaction.user, f"/apelidar usuario={usuario.id} apelido='{apelido}'", "Sucesso")
            logger.info(f"Apelido '{apelido}' definido para {usuario.name} (ID: {usuario.id}) por {interaction.user.name} (ID: {interaction.user.id})")
        else:
            await interaction.response.send_message(
                f"⚠️ Erro ao definir apelido: {message}",
                ephemeral=True
            )
            log_command("ERRO", interaction.user, f"/apelidar usuario={usuario.id} apelido='{apelido}'", f"Erro: {message}")
            logger.error(f"Erro ao definir apelido para usuário {usuario.id}: {message}")

async def setup(bot: commands.Bot):
    """
    Configuração do módulo de comandos administrativos.

    Args:
        bot: O bot do Discord.
    """
    await bot.add_cog(AdminCommands(bot))
    logger.info("Módulo de comandos administrativos carregado")