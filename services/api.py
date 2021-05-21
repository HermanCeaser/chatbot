# TODO
# Incoporate Async/Await in api calls

from asyncio.tasks import gather
import aiohttp
import asyncio
import json
from requests.models import HTTPError
from aiohttp import ClientSession
import time 

start_time = time.time()

async def fetch(session, url):
    """Helper Function to fetch data From API given a Url

    Args:
        session (Session): [A session Object]
        url (URL): [A url Endpoint to an api resource]

    Returns:
        [type]: [description]
    """
    async with session.get(url) as response:
        try:
            data = await response.json()
        except HTTPError as http_error:
            print(f"Failed to make request due to : {http_error}")
            return None
        except Exception as err:
            print(f"An error occured: {err}")
            return None
        return data 


def clean_and_write_json(response, endpoint):
    """Get data from response object and write it to a json file

    """
    if response is not None:
        with open(f"{endpoint}.json", "w") as f:
            json.dump({endpoint: response}, f)
        print(f"Successfully fetched {endpoint} from Api and written results in {endpoint}.json")
    else:
        print("There were no results to fetch from the api")
            


async def getInsuranceProviders(session, url):
    """Hit Providers endpoint and get a list of providers

    Returns:
        [list]: [returns a list of dictionaries with provider names and their respective policies]
    """
    endpoint = 'providers'
    url = url + endpoint

    data = await fetch(session, url)
    clean_and_write_json(data, endpoint)

async def getInsuranceCategories(session, url):
    """Hit categories endpoint and get a list of insurance policies' categories

    Args:
        session (httpSession): 
        url (HttpURL): [get Root URL of the API]
    """
    endpoint = 'categories'
    url = url + endpoint

    data = await fetch(session, url)
    clean_and_write_json(data, endpoint)

async def main():
    """Fetch Data From API and store it in a json file
    """
    url = 'https://myvidabot.herokuapp.com/api/v1/'
    # Use a single Http Session and query Api to get provider and category data
    async with aiohttp.ClientSession() as session:

        # Run the tasks concurrently for Efficiency
        await asyncio.gather(
            getInsuranceProviders(session, url),
            getInsuranceCategories(session, url)
        )

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
end_time = time.time()-start_time
print(f"------ It Took {end_time} seconds ------")
