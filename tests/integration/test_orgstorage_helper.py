import os.path
import uuid
import pytest
from source.common.helpers.orgstorage import OrgStorage


@pytest.fixture(scope="module")
def org_id():
    return str(uuid.uuid4())


@pytest.fixture(scope="module")
def space_id():
    return str(uuid.uuid4())


@pytest.fixture(autouse=True, scope="module")
def cleanup(org_id):
    """Clean up org directory after all tests in this module complete"""
    yield

    if OrgStorage().storage_adapter.fs.exists(org_id):
        OrgStorage().storage_adapter.fs.delete(org_id, recursive=True)


def test_singleton_instance():
    """Test that OrgStorage maintains singleton pattern"""
    instance1 = OrgStorage.get_instance()
    instance2 = OrgStorage.get_instance()

    assert instance1 is instance2


def test_directory_structure(org_id, space_id):
    """Test that the directory structure is created correctly"""
    orgstorage_fs = OrgStorage().storage_adapter.fs

    # Access an org, and it should create the org directory
    OrgStorage().org(org_id)
    assert orgstorage_fs.exists(org_id)

    # Access a directory in the org, and it should create the directory
    OrgStorage().org(org_id).dir('temp')
    assert orgstorage_fs.exists(os.path.join(org_id, 'temp'))

    # Access a space in the org, and it should create the space directory
    space = OrgStorage().org(org_id).space(space_id)
    
    # Add debugging to see what's actually created
    print(f"Base path: {orgstorage_fs.root_marker}")
    print(f"Looking for: {os.path.join(org_id, 'spaces', space_id)}")
    print(f"Available files: {orgstorage_fs.ls(org_id)}")
    
    assert orgstorage_fs.exists(os.path.join(org_id, 'spaces', space_id))


def test_org_dir_fs(org_id):
    """Test basic file operations in an org directory context"""
    # Get org storage instance and create temp directory
    temp_dir_fs = OrgStorage().org(org_id).dir('temp').fs

    # Test file write and read
    test_file = "test.txt"
    test_content = "Hello, World!"

    with temp_dir_fs.open(test_file, 'w') as f:
        f.write(test_content)

    with temp_dir_fs.open(test_file, 'r') as f:
        content = f.read()

    assert content == test_content

    # Test file exists
    assert temp_dir_fs.exists(test_file)

    # Test file deletion
    temp_dir_fs.delete(test_file)
    assert not temp_dir_fs.exists(test_file)


def test_org_space_fs(org_id, space_id):
    """Test basic file operations in an org space context"""
    # Get org storage instance and create space
    space_fs = OrgStorage().org(org_id).space(space_id).fs

    # Test file write and read
    test_file = "space_file.txt"
    test_content = "Space content"

    with space_fs.open(test_file, 'w') as f:
        f.write(test_content)

    with space_fs.open(test_file, 'r') as f:
        content = f.read()

    assert content == test_content

    # Test file exists
    assert space_fs.exists(test_file)

    # Test file deletion
    space_fs.delete(test_file)
    assert not space_fs.exists(test_file)
