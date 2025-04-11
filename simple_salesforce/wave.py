""" Classes for interacting with Salesforce CRM Analytics / Tableau CRM / Einstein Analytics / Wave Analytics API """

import json
import requests
from collections import OrderedDict

from .util import call_salesforce


class WaveHandler:
    """
    CRM Analytics / Tableau CRM / Einstein Analytics / Wave Analytics API handler.
    """

    def __init__(self, headers, wave_url, proxies=None, session=None):
        """Initialize the instance with the given parameters.

        Arguments:

        * headers -- Retrieve the headers
        * wave_url -- Wave API endpoint set in Salesforce instance
        * proxies -- the optional map of scheme to proxy server
        * session -- Custom requests session, created in calling code. This
                     enables the use of requests Session features not otherwise
                     exposed by simple_salesforce.
        """
        self.headers = headers
        self.session = session or requests.Session()
        self.wave_url = wave_url
        self.runnable_resources = [
            'dataConnectors',
            'dataflows',
            'recipes',
        ]
        self.other_resources = [
            'annotations',
            'collections',
            'dashboards',
            'dataflowjobs',
            'datasets',
            'folders',
            'lenses',
            'replicatedDatasets',
            'subscriptions',
            'templates',
            'watchlist',
        ]
        self.available_resources = list(
            set(self.runnable_resources + self.other_resources))
        self.warning = 'Please double check the documentation at https://developer.salesforce.com/docs/atlas.en-us.bi_dev_guide_rest.meta/bi_dev_guide_rest/bi_rest_overview.htm'
        # don't wipe out original proxies with None
        if not session and proxies is not None:
            self.session.proxies = proxies

    def list_resource(self, resource_name, resource_id=None):
        """
        Return specified resources. If resource_id is passed to the function, the specific id will be queried.
        Supported resource name includes:
        annotations -- Returns a list of annotations.
        collections -- Returns a list of collections or creates a collection. Each collection contains Tableau CRM resource items.
        dashboards -- Returns a list of Tableau CRM dashboards or creates a dashboard.
        dataConnectors -- Returns a collection of Tableau CRM connectors and creates a Tableau CRM connector.
        dataflowjobs -- Returns a list of dataflow jobs and starts a new dataflow job. Includes standard dataflows and recipes.
        dataflows -- Returns a collection of dataflows.
        datasets -- Returns a collection of Tableau CRM datasets and creates a new dataset.
        folders -- Returns a collection of applications or folders and creates an Tableau CRM application, which is a folder that contains Tableau CRM datasets, lenses, and dashboards.
        lenses -- Returns a list of Tableau CRM lenses or creates a lens.
        recipes -- Returns a collection of Data Prep recipes and creates a recipe.
        replicatedDatasets -- Returns a list of replicated datasets, also know as connected objects.
        subscriptions -- Returns a list of subscriptions or creates a subscription schedule.
        templates -- Returns a list of Tableau CRM templates, or creates a template.
        watchlist -- Return, create, and update a watchlist.


        Arguments:

        * resource_name -- the resource name to query. Options have been listed above
        * resource_id -- [Optional] if resource id is specified, it will only query the specified resource
        """
        if resource_name in self.available_resources:
            url = self.wave_url + resource_name + "/"
            if resource_id is not None:
                url += resource_id
                # Recipes require pass format=R3 per API documentation
                if resource_name == 'recipes':
                    url += '?format=R3'
            result = call_salesforce(url=url, method='GET',
                                     session=self.session, headers=self.headers)
            response = result.json(object_pairs_hook=OrderedDict)
            if resource_name in response.keys():
                response = response[resource_name]
            return response
        else:
            raise Exception("Unknown Resources." + self.warning)

    def run_resource(self, resource_name, resource_id, is_target_dataflow=True):
        """
        Run the resource manually.

        Arguments:
        * resource_name -- the resource name to trigger the manual run
        * resource_id -- the resource id to trigger to the manual run
        * is_target_dataflow -- [optional] it will only be used when
        resource_name is recipe. recipe is triggered using the same api that dataflow requires.
        Hence, it is required to convert the recipe id to the target dataflow id.
        """
        if resource_name in self.runnable_resources:
            if resource_name == 'dataConnectors':
                url = self.wave_url + resource_name + "/" + resource_id + "/ingest"
                payload = {}
                call_salesforce(url=url, method='POST', session=self.session,
                                headers=self.headers,
                                data=json.dumps(payload, allow_nan=False))
            else:
                if resource_name == 'recipes' and is_target_dataflow is False:
                    print("Converting recipe id to target dataflow id...")
                    recipe_id = resource_id
                    resource_id = \
                        self.list_resource('recipes', resource_id=recipe_id)[
                            'targetDataflowId']
                    print("Recipe ID " + recipe_id +
                          " has been converted to dataflow id " + resource_id + ".")
                url = self.wave_url + "dataflowjobs/"
                payload = {
                    'dataflowId': resource_id,
                    'command': 'start'
                }
                call_salesforce(url=url, method='POST',
                                session=self.session,
                                headers=self.headers,
                                data=json.dumps(payload, allow_nan=False))
            print("Job submitted successfully!")
        else:
            raise Exception(
                "Resource specified is not runnable." + self.warning)
