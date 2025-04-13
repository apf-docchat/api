from dataclasses import dataclass

from .exceptions import InvalidConfigurationError


@dataclass
class StorageDriverOptions:
    """
    Base class for storage driver options.

    This class provides validation and creation of storage driver configurations,
    ensuring required parameters are present while allowing additional options.
    """
    required_keys = []

    @classmethod
    def from_dict(cls, options_dict: dict) -> 'StorageDriverOptions':
        """
        Create an instance from a dictionary.

        :param options_dict: A dictionary of options
        :return: An instance of StorageDriverOptions with values from the dictionary
        :raises InvalidConfigurationError: If required options are missing
        """
        # Validate that all required keys are present in the options
        missing_keys = [key for key in cls.required_keys if key not in options_dict]
        if missing_keys:
            raise InvalidConfigurationError(
                f"Missing one or more required options for {cls.__name__}: {', '.join(missing_keys)}"
            )

        return cls(**options_dict)


#
# Storage driver option classes for strongly-typed options
#

@dataclass
class LocalStorageDriverOptions(StorageDriverOptions):
    path: str

    required_keys = ["path"]


@dataclass
class S3StorageDriverOptions(StorageDriverOptions):
    bucket_name: str  # S3 bucket name
    region: str  # AWS region
    access_key: str  # AWS access key
    secret_key: str  # AWS secret key

    required_keys = ["bucket_name", "region", "access_key", "secret_key"]
