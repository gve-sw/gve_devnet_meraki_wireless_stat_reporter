import meraki
import json
import os
import config

# Initialize the Meraki dashboard API
dashboard = meraki.DashboardAPI(config.api_key)
orgs = dashboard.organizations.getOrganizations()

# Export the organizations to a JSON file
with open('organizations.json', 'w') as file:
    json.dump(orgs, file, indent=4)

print("Organizations data exported to 'organizations.json'")