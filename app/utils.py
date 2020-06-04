def hash_value(labels, starts):
    hash_str = labels.get("alertname", "") + labels.get("instance", "") + labels.get("severity", "") + starts
    return str(hash(hash_str))


def query_hash_id(hash_id):
    data = Alerts.query.filter_by(hash_id=hash_id).first()
    print(data)

    return data
