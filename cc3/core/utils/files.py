import tempfile


def uploaded_file_to_filename(uploaded_file):
    """
    Either the upload went directly to file, or it is still in memory for
    smaller files.
    Note that the file must be deleted manually!

    Return the complete filename to the uploaded file.
    """
    try:
        filename = uploaded_file.temporary_file_path()
    except AttributeError as e:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        f = open(tmp.name, 'w')
        for chunk in uploaded_file.chunks():
            f.write(chunk)
        f.close()
        filename = tmp.name
    return filename
