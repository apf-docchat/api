import os
import sys

if __name__ == "__main__":
    if len(sys.argv) <= 2:
        print('[org] and [filename] arguments are required')
        sys.exit(1)

    # Make the script think it's running in the pw-vectoriser project
    pw_projects_base_dir = os.path.dirname(os.getcwd())

    sys.path.insert(0, os.path.join(pw_projects_base_dir, 'pw-vectoriser'))

    # Call the vectorize_local_file
    from source.lib.vectorize_local_file import vectorize_local_file

    vectorize_local_file({
        'source_type': 'local_file',
        'org_id': sys.argv[1],
        'filename': sys.argv[2]
    })

    # Remove the pw-vectoriser dir from sys.path
    sys.path.pop(0)

    # Make the script think it's running in the pw-api root dir
    sys.path.insert(0, os.getcwd())

    # Call add_files_to_db
    from source.api.utilities.helper_functions import add_files_to_db

    add_files_to_db(sys.argv[1], sys.argv[2])
