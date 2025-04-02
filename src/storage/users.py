import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import logging

from src.storage.database import get_connection


def register_user(user_id: str, role_or_name: str, role: str = None, registered_by: str = "system") -> Tuple[bool, str]:
    """
    Registra um usuário no sistema.

    Esta função possui duas assinaturas suportadas:
    1. register_user(user_id, role) - Para compatibilidade com código existente
    2. register_user(user_id, user_name, role, registered_by) - Assinatura completa

    Args:
        user_id (str): ID do usuário no Discord.
        role_or_name (str): Papel do usuário ('teammember' ou 'po') OU nome do usuário.
        role (str, opcional): Papel do usuário. Se None, role_or_name é considerado como o papel.
        registered_by (str, opcional): ID do usuário que está registrando.

    Returns:
        Tuple[bool, str]: (Sucesso, Mensagem)
    """
    if role is None:
        role = role_or_name
        user_name = f"User {user_id}"
    else:
        user_name = role_or_name

    if role not in ['teammember', 'po']:
        return False, f"Papel inválido: {role}. Use 'teammember' ou 'po'."

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        existing_user = cursor.fetchone()

        if existing_user:
            cursor.execute(
                "UPDATE users SET role = ?, user_name = ?, registered_by = ? WHERE user_id = ?",
                (role, user_name, registered_by, user_id)
            )
            conn.commit()
            return True, f"Usuário atualizado para papel: {role_display_name(role)}"

        cursor.execute(
            "INSERT INTO users (user_id, user_name, role, registered_by) VALUES (?, ?, ?, ?)",
            (user_id, user_name, role, registered_by)
        )
        conn.commit()
        return True, f"Usuário registrado com sucesso como: {role_display_name(role)}"

    except sqlite3.Error as e:
        return False, f"Erro ao registrar usuário: {str(e)}"

    finally:
        conn.close()


def update_user_nickname(user_id: str, nickname: str, updated_by: str) -> Tuple[bool, str]:
    """
    Atualiza o apelido de um usuário registrado no sistema.

    Args:
        user_id (str): ID do usuário no Discord.
        nickname (str): Novo apelido do usuário.
        updated_by (str): ID do usuário que está atualizando o apelido.

    Returns:
        Tuple[bool, str]: (Sucesso, Mensagem)
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if not user:
            return False, "Usuário não encontrado no sistema."

        cursor.execute(
            "UPDATE users SET nickname = ? WHERE user_id = ?",
            (nickname, user_id)
        )
        conn.commit()

        return True, f"Apelido do usuário atualizado com sucesso para: {nickname}"

    except sqlite3.Error as e:
        return False, f"Erro ao atualizar apelido do usuário: {str(e)}"

    finally:
        conn.close()


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Obtém informações de um usuário pelo ID.

    Args:
        user_id (str): ID do usuário no Discord.

    Returns:
        Optional[Dict[str, Any]]: Informações do usuário ou None se não encontrado.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if user:
            return dict(user)
        return None

    except sqlite3.Error:
        return None

    finally:
        conn.close()


def get_users_by_role(role: str) -> List[Dict[str, Any]]:
    """
    Obtém todos os usuários com um determinado papel.

    Args:
        role (str): Papel do usuário ('teammember' ou 'po').

    Returns:
        List[Dict[str, Any]]: Lista de usuários com o papel especificado.
    """
    logger = logging.getLogger('team_analysis_bot')

    logger.debug(f"Iniciando busca de usuários com papel '{role}'")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        if role == "all":
            logger.debug("Buscando todos os usuários (all)")
            cursor.execute("SELECT * FROM users")
        else:
            logger.debug(f"Buscando usuários com papel específico: {role}")
            cursor.execute("SELECT * FROM users WHERE role = ?", (role,))

        users = cursor.fetchall()

        if users:
            logger.debug(f"Encontrados {len(users)} usuários com papel '{role}'")
        else:
            logger.debug(f"Nenhum usuário encontrado com papel '{role}'")

        result = [dict(user) for user in users]
        logger.debug(f"Lista convertida para dicionários com {len(result)} itens")

        return result

    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar usuários com papel '{role}': {str(e)}")
        return []

    finally:
        conn.close()
        logger.debug("Conexão com o banco de dados fechada")


def remove_user(user_id: str) -> Tuple[bool, str]:
    """
    Remove um usuário do sistema.

    Args:
        user_id (str): ID do usuário no Discord.

    Returns:
        Tuple[bool, str]: (Sucesso, Mensagem)
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if not user:
            return False, "Usuário não encontrado."

        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()

        return True, f"Usuário removido com sucesso."

    except sqlite3.Error as e:
        return False, f"Erro ao remover usuário: {str(e)}"

    finally:
        conn.close()


def role_display_name(role: str) -> str:
    """
    Retorna o nome de exibição para um papel.

    Args:
        role (str): Papel do usuário ('teammember' ou 'po').

    Returns:
        str: Nome de exibição do papel.
    """
    if role == 'teammember':
        return "Team Member"
    elif role == 'po':
        return "Product Owner"
    else:
        return role.capitalize()


def check_user_is_po(user_id: str) -> bool:
    """
    Verifica se um usuário tem o papel de Product Owner.

    Args:
        user_id (str): ID do usuário no Discord.

    Returns:
        bool: True se for PO, False caso contrário.
    """
    user = get_user(user_id)
    return user is not None and user.get('role') == 'po'


def get_user_display_name(user_id: str, user_obj: Optional[Dict[str, Any]] = None) -> str:
    """
    Retorna o nome de exibição do usuário, priorizando o apelido se estiver definido.

    Args:
        user_id (str): ID do usuário no Discord.
        user_obj (Optional[Dict[str, Any]], optional): Objeto de usuário já carregado,
                                                     para evitar consulta ao banco.

    Returns:
        str: Nome de exibição do usuário.
    """
    user = user_obj if user_obj is not None else get_user(user_id)
    if not user:
        return f"User {user_id}"

    if user.get('nickname'):
        return user['nickname']

    return user['user_name']