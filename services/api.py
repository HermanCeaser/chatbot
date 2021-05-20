# TODO
# Incoporate Async/Await in api calls

import aiohttp
import asyncio
import json
from requests.models import HTTPError


class VidabotApi(object):
    """An Api class that queries the vidabot api and returns results based on intent

    """
    pass

api_address = 'https://myvidabot.herokuapp.com/api/v1/'

async def getInsuranceProviders(session, url):
    """Hit Providers endpoint and get a list of providers

    Returns:
        [list]: [returns a list of dictionaries with provider names and their respective policies]
    """
    endpoint = 'providers'
    url = url+endpoint

    async with session.get(url) as response:
        try:
            data = await response.json()
        except HTTPError as http_error:
            print(f"Failed to make request due to : {http_error}")
            return None
        except Exception as err:
            print(f"An error occured: {err}")
            return None
        providers = [provider['provider_name'] for provider in data ]
        return data

async def main():
    """Fetch Data From API and store it in a json file
    """
    async with aiohttp.ClientSession() as session:
        response = await getInsuranceProviders(session, api_address)
        providers = {'providers': response}

        with open("providers.json", "w") as f:
            json.dump(providers, f)
            print("Successfully fetched providers from API")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())

