class OpenAiApiResponseParser:
    def __init__(self, data):
        self.data = data

    def parse(self):
        incident_data = None
        component_impacts_data = None
        incident_links = self.data['incident_links']
        component_impacts = self.data['component_impacts']
        if incident_links:
            incident_data = incident_links[-1]
        if component_impacts:
            component_impacts_data = component_impacts[-1]

        result = {}
        if incident_data and component_impacts_data:
            result = {
                "component_impacts": {
                    "status_page_incident_id": component_impacts_data['status_page_incident_id'],
                    "status": component_impacts_data['status']
                },
                "incident_links": {
                    "name": incident_data["name"],
                    "status": incident_data["status"],
                    "permalink": incident_data["permalink"]
                }
            }
            if result and result.get('component_impacts', {}).get('status') != 'resolved':
                return {
                    "status": result.get('component_impacts', {}).get('status'),
                    "name": incident_data["name"]
                }
                # return {
                #     "status": 'partially degrated',
                #     "name": 'waste of time'
                # }
        return {}
