from threading import Lock

from fsspec import AbstractFileSystem

from source.common.app_config import config
from source.common.utils.storage_adapter import StorageAdapter, StorageDriverRegistry


class AppData:
    _instance = None
    _lock = Lock()

    def __init__(self):
        self._initialize()

    def _initialize(self):
        driver_type = config.get('appdata.driver.type', 'local')
        driver = StorageDriverRegistry.get(driver_type)
        driver_options = driver.options.from_dict(config.get('appdata.driver.options', {}))
        self._storage_adapter = StorageAdapter(driver, driver_options)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def storage_adapter(self) -> StorageAdapter:
        return self._storage_adapter

    @property
    def fs(self) -> AbstractFileSystem:
        return self.get_instance().storage_adapter.fs
