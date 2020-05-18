
@app.route('/receive', methods=['POST', 'GET'])
def get_data():
    if request.method == 'POST':
        data = request.get_json()
        types_incidents = db.session.query(TypeOfIncident.id, TypeOfIncident.labels).filter(TypeOfIncident.active == True).all()
        num_alert = len(data)
        incidents = defaultdict(list)
        for alert in data:
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
