generate_file_upload_schema = {
    'type': 'object',
    'properties': {
        'file_name': {'type': 'string'}
    },
    'required': ['file_name']
}

post_upload_schema = {
    'type': 'object',
    'properties': {
        'file_key': {'type': 'string'},
        'file_category': {'type': 'string'},
        'original_file_name': {'type': 'string'}
    },
    'required': [
        'file_key', 'file_category', 'original_file_name'
    ]
}

retrieve_file_schema = {
    'type': 'object',
    'properties': {
        'file_store_id': {'type': 'integer'},
        'file_key': {'type': 'string'}
    },
    'required': [
        'file_store_id', 'file_key'
    ]
}
