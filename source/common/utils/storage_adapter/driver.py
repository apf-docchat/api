from typing import Type, Callable

import fsspec
from fsspec import AbstractFileSystem
from fsspec.implementations.dirfs import DirFileSystem

from .driver_options import LocalStorageDriverOptions, S3StorageDriverOptions, StorageDriverOptions


class StorageDriver:
    def __init__(
            self,
            fs_factory: Callable[[StorageDriverOptions], AbstractFileSystem],
            options_class: Type[StorageDriverOptions],
    ) -> None:
        self._fs_factory = fs_factory
        self._options_class = options_class

    def init_fs(self, driver_options: StorageDriverOptions) -> AbstractFileSystem:
        if not isinstance(driver_options, self._options_class):
            raise TypeError(
                f"Expected options of type {self._options_class.__name__}, got {type(driver_options).__name__}")
        return self._fs_factory(driver_options)

    @property
    def options(self) -> Type[StorageDriverOptions]:
        return self._options_class


class StorageDriverRegistry:
    _registry: dict[str, StorageDriver] = {}

    @classmethod
    def register(cls, name: str, driver: StorageDriver) -> None:
        cls._registry[name] = driver

    @classmethod
    def get(cls, name: str) -> StorageDriver:
        if name not in cls._registry:
            raise ValueError(f"Unknown driver: {name}. Available drivers: {', '.join(cls._registry.keys())}")
        return cls._registry[name]


# Register default drivers
StorageDriverRegistry.register('local', StorageDriver(
    lambda options: DirFileSystem(fs=fsspec.filesystem('file', **options.__dict__), path=options.path),
    LocalStorageDriverOptions,
))

StorageDriverRegistry.register('s3', StorageDriver(
    lambda options: fsspec.filesystem('s3', **options.__dict__),
    S3StorageDriverOptions,
))
