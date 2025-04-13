from source.common.app_config import config


def module_supports_mimetype(module_name: str, mimetype: str) -> bool:
    """
    Check if the given mimetype is supported for the specified module.

    Args:
        module_name (str): The name of the module to check (e.g., 'docchat').
        mimetype (str): The mimetype to verify (e.g., 'application/pdf').

    Returns:
        bool: True if the mimetype is supported, False otherwise.

    Raises:
        ValueError: If the module_name is not in SUPPORTED_MODULES or if mimetype is empty.

    Example:
        >>> module_supports_mimetype('docchat', 'application/pdf')
        True
    """

    if module_name not in config.get('modules.enabled'):
        raise ValueError(f"Unsupported module: {module_name}")

    return mimetype in config.get(f'modules.enabled.{module_name}', list())


def check_module_supports_mimetype(module_name: str, mimetype: str) -> bool:
    if not module_supports_mimetype(module_name, mimetype):
        raise ValueError(f"File type {mimetype} is not supported for module {module_name}")

    return True
