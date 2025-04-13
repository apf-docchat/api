from source.common.helpers.appdata import AppData


def test_fs():
    # Get the filesystem from AppData
    fs = AppData().fs

    test_file = "test_file.txt"
    test_content = "Hello, AppData!"

    # Write content to file
    with fs.open(test_file, 'w') as f:
        f.write(test_content)

    # Check if file exists
    assert fs.exists(test_file), "File should exist after writing"

    # Verify content
    with fs.open(test_file, 'r') as f:
        content = f.read()
    assert content == test_content, "File content should match what was written"

    # Test file deletion
    fs.delete(test_file)
    assert not fs.exists(test_file)
