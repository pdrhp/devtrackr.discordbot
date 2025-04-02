import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from src.utils.config import get_env, log_command
from src.storage.users import get_users_by_role, get_user

logger = logging.getLogger('team_analysis_bot')

class UserCommands(commands.Cog):
    """Comandos relacionados a gerenciamento de usuários."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="listar-usuarios", description="Lista todos os usuários registrados")
    @app_commands.describe(tipo="Tipo de usuário a listar")
    @app_commands.choices(tipo=[
        app_commands.Choice(name="Team Members", value="teammember"),
        app_commands.Choice(name="Product Owners", value="po"),
        app_commands.Choice(name="Todos", value="all")
    ])
    async def list_users(
        self,
        interaction: discord.Interaction,
        tipo: str = "all"
    ):
        """
        Lista todos os usuários registrados.

        Args:
            interaction: A interação do Discord.
            tipo: Tipo de usuário a listar.
        """
        logger = logging.getLogger('team_analysis_bot')
        logger.debug(f"Comando listar-usuarios iniciado com tipo={tipo}")

        await interaction.response.defer(ephemeral=True)
        logger.debug("Resposta deferida para evitar timeout")

        try:
            logger.debug(f"Obtendo usuários do tipo: {tipo}")
            users = get_users_by_role(tipo)
            logger.debug(f"Retornados {len(users) if users else 0} usuários")

            if not users:
                await interaction.followup.send(
                    f"⚠️ Não há usuários do tipo '{tipo}' registrados.",
                    ephemeral=True
                )
                log_command("INFO", interaction.user, f"/listar-usuarios tipo={tipo}", "Nenhum usuário encontrado")
                logger.info(f"Nenhum usuário do tipo '{tipo}' encontrado")
                return

            logger.debug("Iniciando processamento dos usuários para exibição")
            user_strings = []

            guild = interaction.guild

            batch_size = 5
            total_users = len(users)

            for i in range(0, total_users, batch_size):
                batch = users[i:i+batch_size]
                batch_strings = []

                for j, user_data in enumerate(batch):
                    user_id = user_data["user_id"]
                    user_index = i + j
                    logger.debug(f"Processando usuário {user_index+1}/{total_users}: ID={user_id}")

                    nickname = user_data.get("nickname")

                    try:
                        if guild:
                            member = guild.get_member(int(user_id))
                            if member:
                                display_name = member.display_name
                                if nickname:
                                    user_string = f"• {member.mention} ({display_name}) - ({nickname})"
                                else:
                                    user_string = f"• {member.mention} ({display_name})"
                                logger.debug(f"Usuário {user_id} encontrado localmente: {display_name}")
                                batch_strings.append(user_string)
                                continue

                        user = await self.bot.fetch_user(int(user_id))
                        display_name = user.display_name
                        if nickname:
                            user_string = f"• {user.mention} ({display_name}) - ({nickname})"
                        else:
                            user_string = f"• {user.mention} ({display_name})"
                        logger.debug(f"Usuário {user_id} encontrado via API: {display_name}")

                    except Exception as e:
                        if nickname:
                            user_string = f"• ID: {user_id} (Usuário não encontrado) - ({nickname})"
                        else:
                            user_string = f"• ID: {user_id} (Usuário não encontrado)"
                        logger.error(f"Erro ao buscar usuário {user_id}: {str(e)}")

                    batch_strings.append(user_string)

                user_strings.extend(batch_strings)

                if (i + batch_size) % 10 == 0 and i > 0 and i + batch_size < total_users:
                    progress = min(100, int(((i + batch_size) / total_users) * 100))
                    logger.debug(f"Progresso: {progress}% ({i + batch_size}/{total_users})")

            tipo_display = {
                "teammember": "Team Members",
                "po": "Product Owners",
                "all": "Todos os Usuários"
            }.get(tipo, tipo)

            logger.debug(f"Criando embed com {len(user_strings)} usuários")

            if len("\n".join(user_strings)) > 4000:
                logger.warning(f"Lista de usuários muito grande ({len(user_strings)} usuários), dividindo em múltiplas mensagens")

                page_size = 20
                pages = [user_strings[i:i + page_size] for i in range(0, len(user_strings), page_size)]
                logger.debug(f"Lista dividida em {len(pages)} páginas")

                for i, page in enumerate(pages):
                    page_embed = discord.Embed(
                        title=f"📋 Lista de Usuários: {tipo_display} - Página {i+1}/{len(pages)}",
                        description="\n".join(page),
                        color=discord.Color.blue()
                    )
                    page_embed.set_footer(text=f"Total: {len(users)} usuários (Mostrando {i*page_size+1}-{min((i+1)*page_size, len(users))})")

                    await interaction.followup.send(embed=page_embed, ephemeral=True)
                    logger.debug(f"Enviada página {i+1}/{len(pages)}")

                log_command("LISTAGEM", interaction.user, f"/listar-usuarios tipo={tipo}", f"Listados {len(users)} usuários em {len(pages)} páginas")
                logger.info(f"Listados {len(users)} usuários do tipo '{tipo}' em {len(pages)} páginas para {interaction.user.name} (ID: {interaction.user.id})")
            else:
                embed = discord.Embed(
                    title=f"📋 Lista de Usuários: {tipo_display}",
                    description="\n".join(user_strings) if user_strings else "Nenhum usuário encontrado.",
                    color=discord.Color.blue()
                )

                embed.set_footer(text=f"Total: {len(users)} usuários")

                logger.debug("Enviando resposta com a lista de usuários")
                await interaction.followup.send(embed=embed, ephemeral=True)
                log_command("LISTAGEM", interaction.user, f"/listar-usuarios tipo={tipo}", f"Listados {len(users)} usuários")
                logger.info(f"Listados {len(users)} usuários do tipo '{tipo}' para {interaction.user.name} (ID: {interaction.user.id})")

        except Exception as e:
            logger.error(f"Erro não tratado no comando listar-usuarios: {str(e)}", exc_info=True)
            await interaction.followup.send(
                f"⚠️ Ocorreu um erro ao processar o comando: {str(e)}",
                ephemeral=True
            )
            log_command("ERRO", interaction.user, f"/listar-usuarios tipo={tipo}", f"Erro: {str(e)}")