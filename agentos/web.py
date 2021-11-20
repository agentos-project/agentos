import yaml
import json
import pprint
import requests

AOS_WEB_BASE_URL = "http://localhost:8000"


def push_component_spec(frozen_spec):
    url = f"{AOS_WEB_BASE_URL}/registry/api/v2/components/ingest_spec/"
    data = {"components.yaml": yaml.dump(frozen_spec)}
    result = requests.post(url, data=data)
    result.raise_for_status()
    print("\nResults:")
    pprint.pprint(json.loads(result.content))
    print()
