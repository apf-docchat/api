import magic


def check_mimetype_matches_declared(content: bytes, declared_mime_type: str) -> bool:
    """
    Validate MIME types and module support for file uploads.
    Returns the actual mime type if validation passes.
    """
    actual_mime_type = magic.from_buffer(content, mime=True)

    if actual_mime_type != declared_mime_type:
        raise RuntimeError(
            f"Declared MIME type ({declared_mime_type}) doesn't match actual content type ({actual_mime_type})")

    return True
