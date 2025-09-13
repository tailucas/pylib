from .config import log, creds

def is_flag_enabled(flag_name: str) -> bool:
    """
    Check if a feature flag is enabled.

    Args:
        flag_name (str): The name of the feature flag to check.

    Returns:
        bool: True if the feature flag is enabled, False otherwise.
    """
    flag_value = creds.get_creds(f'flags/{flag_name}/value').strip().lower()
    is_enabled = flag_value in ['true', '1', 'yes']
    log.debug(f"Feature flag '{flag_name}' is set to '{flag_value}'. Enabled: {is_enabled}")
    return is_enabled