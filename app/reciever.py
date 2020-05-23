def hash_value(labels, starts):
    hash_str = labels.get("alertname", "") + labels.get("instance", "") + starts

    return hash(hash_str)


def query_hash_id(hash_id):
    data = Alerts.query.filter_by(hash_id=hash_id).first()

    return data


@app.route('/receive', methods=['POST', 'GET'])
def get_data():
    if request.method == 'POST':
        data = request.get_json()
        types_incidents = db.session.query(TypeOfIncident.id, TypeOfIncident.labels).filter(TypeOfIncident.active == True).all()
        num_alert = len(data)
        incidents = defaultdict(list)
        for alert in data:
            if alert.get("status") != "resolved":
                continue
            
            hash_str = hash_value(alert["labels"], alert["startsAt"])
            if hash_str and not query_hash_id(hash_str):
                alert["hash_id"] = hash_str
                labels = alert['labels'].values()
                for type_ in types_incidents:
                    correct_type = True
                    for label in type_[1].split():
                        if label not in labels:
                            correct_type = False
                            break
                    if correct_type:
                        incidents[type_[0]].append(alert)
        for incident in incidents.items():
            create_incident(incident)
            
        return jsonify(data)
    return "no item"

