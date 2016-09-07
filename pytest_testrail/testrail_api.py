#
# TestRail API binding for Python 2.x (API v2, available since
# TestRail 3.0)
#
# Learn more:
#
# http://docs.gurock.com/testrail-api2/start
# http://docs.gurock.com/testrail-api2/accessing
#
# Copyright Gurock Software GmbH. See license.md for details.
#

import requests


class APIClient:
    def __init__(self, base_url):
        self.user = ''
        self.password = ''
        if not base_url.endswith('/'):
            base_url += '/'
        self.__url = base_url + 'index.php?/api/v2/'
        self.headers = {'Content-Type': 'application/json'}

    #
    # Send Get
    #
    # Issues a GET request (read) against the API and returns the result
    # (as Python dict).
    #
    # Arguments:
    #
    # uri                 The API method to call including parameters
    #                     (e.g. get_case/1)
    #
    def send_get(self, uri):
        url = self.__url + uri
        e = None

        try:
            r = requests.get(
                url,
                auth=(self.user, self.password),
                headers=self.headers
            )
            return r.json()
        except requests.RequestException as e:
            return e.response.text()

    #
    # Send POST
    #
    # Issues a POST request (write) against the API and returns the result
    # (as Python dict).
    #
    # Arguments:
    #
    # uri                 The API method to call including parameters
    #                     (e.g. add_case/1)
    # data                The data to submit as part of the request (as
    #                     Python dict, strings must be UTF-8 encoded)
    #
    def send_post(self, uri, data):
        url = self.__url + uri
        e = None

        try:
            r = requests.post(
                url,
                auth=(self.user, self.password),
                headers=self.headers,
                data=data
            )
            return r.json()
        except requests.RequestException as e:
            return e.response.text()
