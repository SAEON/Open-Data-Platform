import requests
from fastapi.exceptions import HTTPException
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE, HTTP_404_NOT_FOUND, HTTP_405_METHOD_NOT_ALLOWED

from odp.api.models.datacite import DataCiteMetadata, DataCiteMetadataList


class DataCiteClient:

    def __init__(
            self,
            api_url: str,
            doi_prefix: str,
            username: str,
            password: str,
    ):
        self.api_url = api_url
        self.doi_prefix = doi_prefix
        self.username = username
        self.password = password
        self.timeout = 60.0

    def list_dois(self, page_size: int, page_num: int) -> DataCiteMetadataList:
        """
        Get a list of metadata records from DataCite, which have a DOI matching
        our configured prefix.

        Note: Using DataCite's ``page[number]`` query parameter we can fetch a
        maximum of 10,000 records in total. If this limit becomes problematic,
        we will have to switch to using the ``page[cursor]`` query parameter.
        DataCite's pagination methods are described here:
        https://support.datacite.org/docs/pagination

        :param page_size: the number of records to be returned per page
        :param page_num: the page number
        :return: DataCiteMetadataList
        """
        result = self._request('GET', '/dois/', params={
            'query': f'id:{self.doi_prefix}/*',
            'page[size]': page_size,
            'page[number]': page_num,
        })

        return DataCiteMetadataList(
            records=[DataCiteMetadata(
                doi=item['id'],
                url=item['attributes']['url'],
                metadata=item['attributes'],
            ) for item in result['data']],
            total_records=result['meta']['total'],
            total_pages=result['meta']['totalPages'],
            this_page=result['meta']['page'],
        )

    def get_doi(self, doi: str) -> DataCiteMetadata:
        """
        Fetch a metadata record from DataCite.

        :param doi: the DOI string
        :return: DataCiteMetadata
        """
        result = self._request('GET', f'/dois/{doi}')

        return DataCiteMetadata(
            doi=result['data']['id'],
            url=result['data']['attributes']['url'],
            metadata=result['data']['attributes'],
        )

    def publish_doi(self, doi: str, url: str, metadata: dict) -> DataCiteMetadata:
        """
        Publish a DOI and associated metadata to DataCite. This creates or updates
        the record on DataCite servers, and sets its state to ``findable``.

        :param doi: the DOI string
        :param url: the metadata landing page in the ODP
        :param metadata: the metadata dictionary
        :return: DataCiteMetadata
        """
        metadata['url'] = url
        metadata['event'] = 'publish'
        payload = {
            'data': {
                'id': doi,
                'attributes': metadata,
            }
        }
        result = self._request('PUT', f'/dois/{doi}', json=payload)

        return DataCiteMetadata(
            doi=result['data']['id'],
            url=result['data']['attributes']['url'],
            metadata=result['data']['attributes'],
        )

    def unpublish_doi(self, doi: str) -> None:
        """
        Un-publish a DOI from DataCite. This attempts a delete, falling
        through to an update of the metadata record on DataCite servers
        that sets its state to ``registered``.

        :param doi: the DOI string
        """
        try:
            self._request('DELETE', f'/dois/{doi}')
            return  # it was a draft DOI and could be deleted
        except HTTPException as e:
            if e.status_code == HTTP_404_NOT_FOUND:
                pass  # nothing to do
            elif e.status_code == HTTP_405_METHOD_NOT_ALLOWED:
                # the DOI has already been registered and/or published;
                # it cannot be deleted so we hide it
                payload = {
                    'data': {
                        'id': doi,
                        'attributes': {'event': 'hide'},
                    }
                }
                self._request('PUT', f'/dois/{doi}', json=payload)
            else:
                raise

    def _request(self, method, path, **kwargs):
        headers = {}
        if method in ('GET', 'POST', 'PUT'):
            headers['Accept'] = 'application/vnd.api+json'
        if method in ('POST', 'PUT'):
            headers['Content-Type'] = 'application/vnd.api+json'
        try:
            r = requests.request(method, self.api_url + path, **kwargs,
                                 auth=(self.username, self.password),
                                 timeout=self.timeout,
                                 headers=headers)
            r.raise_for_status()
            if r.content:
                return r.json()

        except requests.HTTPError as e:
            try:
                error_detail = e.response.json()
            except ValueError:
                error_detail = e.response.reason
            raise HTTPException(status_code=e.response.status_code, detail=error_detail)

        except requests.RequestException as e:
            raise HTTPException(status_code=HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
