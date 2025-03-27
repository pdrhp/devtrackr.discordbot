"""
Módulo de controle de funcionalidades para Team Analysis Discord Bot.
"""
import json
import os
from typing import Dict, Optional

FEATURE_TOGGLE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                  "data", "feature_toggles.json")

os.makedirs(os.path.dirname(FEATURE_TOGGLE_FILE), exist_ok=True)

DEFAULT_FEATURES = {
    "ponto": False,
}


def load_feature_toggles() -> Dict[str, bool]:
    """
    Carrega as configurações de funcionalidades do arquivo de configuração.

    Returns:
        Dict[str, bool]: Dicionário contendo nomes das funcionalidades e seus status.
    """
    if not os.path.exists(FEATURE_TOGGLE_FILE):
        save_feature_toggles(DEFAULT_FEATURES)
        return DEFAULT_FEATURES.copy()

    try:
        with open(FEATURE_TOGGLE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return DEFAULT_FEATURES.copy()


def save_feature_toggles(features: Dict[str, bool]) -> None:
    """
    Salva as configurações de funcionalidades no arquivo de configuração.

    Args:
        features (Dict[str, bool]): Dicionário contendo nomes das funcionalidades e seus status.
    """
    os.makedirs(os.path.dirname(FEATURE_TOGGLE_FILE), exist_ok=True)
    with open(FEATURE_TOGGLE_FILE, 'w', encoding='utf-8') as f:
        json.dump(features, f, indent=4)


def is_feature_enabled(feature_name: str) -> bool:
    """
    Verifica se uma funcionalidade específica está ativada.

    Args:
        feature_name (str): Nome da funcionalidade a verificar.

    Returns:
        bool: True se a funcionalidade estiver ativada, False caso contrário.
    """
    features = load_feature_toggles()
    return features.get(feature_name, False)


def toggle_feature(feature_name: str) -> bool:
    """
    Alterna uma funcionalidade entre ativada e desativada.

    Args:
        feature_name (str): Nome da funcionalidade a alternar.

    Returns:
        bool: O novo status da funcionalidade (True para ativada, False para desativada).
    """
    features = load_feature_toggles()

    if feature_name not in features:
        features[feature_name] = False

    features[feature_name] = not features[feature_name]

    save_feature_toggles(features)

    return features[feature_name]