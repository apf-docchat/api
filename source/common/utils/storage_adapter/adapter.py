from typing import Optional

import fsspec

from .driver import StorageDriver

from .exceptions import InvalidConfigurationError
from .driver_options import StorageDriverOptions


class StorageAdapter:
    def __init__(
            self,
            driver: StorageDriver,
            driver_options: Optional[StorageDriverOptions] = None
    ):
        """
        Sets up the storage adapter with the specified driver and options.

        :param driver: The preset name of the storage driver to use (e.g., 'local', 's3'). Can also be a StorageDriver instance.
        :param driver_options: An instance of a StorageDriverOptions subclass.
        :raises InvalidConfigurationError: If the driver or driver options are invalid.
        """
        if not isinstance(driver, StorageDriver):
            raise InvalidConfigurationError("driver must be a StorageDriver instance")

        # Validate driver options if provided
        if driver_options and not isinstance(driver_options, StorageDriverOptions):
            raise InvalidConfigurationError("driver_options must be an instance of StorageDriverOptions")

        self._driver = driver
        self._driver_options = driver_options

        self._fs = self._driver.init_fs(driver_options)

    @property
    def driver(self) -> StorageDriver:
        return self._driver

    @property
    def driver_options(self) -> StorageDriverOptions:
        return self._driver_options

    @property
    def fs(self) -> fsspec.AbstractFileSystem:
        return self._fs
