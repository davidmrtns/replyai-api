def has_entry_with_attr(entries, attr_path, expected_value):
    def get_attr(obj, path):
        for attr in path.split("."):
            obj = getattr(obj, attr, None)
            if obj is None:
                return None
        return obj

    return any(get_attr(payload, attr_path) == expected_value for payload in entries)
