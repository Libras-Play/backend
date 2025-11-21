import requests

# GET Topics devuelve JSONB, así que migration 0006 SÍ se ejecutó
response = requests.get('http://libras-play-dev-alb-1450968088.us-east-1.elb.amazonaws.com/content/api/v1/languages/1/topics?limit=1')
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:500]}")

# Verificar si devuelve JSONB o String
import json
if response.status_code == 200:
    data = response.json()
    if data:
        topic = data[0]
        print(f"\nTopic title type: {type(topic.get('title'))}")
        print(f"Topic title value: {topic.get('title')}")
