from threading import Lock

from fsspec.implementations.dirfs import DirFileSystem

from source.common.app_config import config
from source.common.utils.storage_adapter import StorageAdapter, StorageDriverRegistry


class OrgStorage:
    _instance = None
    _lock = Lock()

    def __init__(self):
        self._initialize()

    def _initialize(self):
        driver_type = config.get('orgstorage.driver.type', 'local')
        driver = StorageDriverRegistry.get(driver_type)
        options = driver.options.from_dict(config.get('orgstorage.driver.options', {}))
        self._storage_adapter = StorageAdapter(driver, options)

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

    def org(self, org_id: str):
        return _OrgContext(self.get_instance().storage_adapter, org_id)


class _OrgContext:
    def __init__(self, storage_adapter: StorageAdapter, org_id: str):
        self._org_id = org_id
        self._storage_adapter = storage_adapter

        # Create the org directory if it doesn't exist
        if not storage_adapter.fs.exists(self._org_id):
            storage_adapter.fs.mkdir(self._org_id)

        self._fs = DirFileSystem(path=self._org_id, fs=storage_adapter.fs)

    def dir(self, directory_name: str):
        return _DirContext(self._fs, directory_name)

    def space(self, space_id: str):
        return _SpaceContext(self._fs, space_id)


class _DirContext:
    def __init__(self, fs: DirFileSystem, dir_name: str):
        self._fs = fs
        self._dir_name = dir_name
        
        # Create the requested directory if it doesn't exist
        if not self._fs.exists(self._dir_name):
            self._fs.mkdir(self._dir_name)

    @property
    def fs(self) -> DirFileSystem:
        return DirFileSystem(path=self._dir_name, fs=self._fs)


class _SpaceContext:
    def __init__(self, fs: DirFileSystem, space_id: str):
        self._dir_context = _DirContext(fs, "spaces")
        self._fs = self._dir_context.fs
        self._space_id = space_id

        # Create the space directory if it doesn't exist
        if not self._fs.exists(self._space_id):
            self._fs.mkdir(self._space_id)
    
    @property
    def fs(self) -> DirFileSystem:
        return DirFileSystem(path=self._space_id, fs=self._fs)
