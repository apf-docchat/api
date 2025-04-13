import logging


def set_debug_logger():
    # Create a logger
    logger = logging.getLogger('my_logger')

    # If the logger has handlers, it already exists, so you can return it
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)  # Set the logging level

    # Create a file handler that logs even debug messages
    fh = logging.FileHandler('log.txt')
    fh.setLevel(logging.DEBUG)

    # Create a formatter and set it for the handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(fh)

    logger.propagate = False

    return logger
