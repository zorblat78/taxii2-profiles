The following map the expected test results for various profiles against STIX inputs

basic_incident_schema.json:
    incident_ransom_no_report.json: reject
    incident_ransom_report.json: accepted
    observed_data_report: reject

basic_incident_schema_no_report.json:
    incident_ransom_no_report.json: accepted
    incident_ransom_report.json: reject
    observed_data_report: reject

sighting.json:
    observed_data_report: accepted
