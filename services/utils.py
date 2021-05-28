# function to list policy categories
import json

policies = json.load(open('categories.json', 'r'))
providers = json.load(open('providers.json', 'r'))

def list_categories():
    return [category_name['name'] for category_name in policies['categories']]

def list_providers():
    return [provider['provider_name'] for provider in providers['providers']]
