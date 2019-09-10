#!/usr/bin/env python

# TODO: find out best practices for storing tokens and credentials, so that you don't immediately pollute your git history. It's about time to make an initial commit.

import sys
import requests
import json
import argparse

from requests.exceptions import HTTPError

# Modified by load_token() 
TOKEN = ''


def create_parser():
    parser = argparse.ArgumentParser(description='Rename files according to tvdb')
    parser.add_argument('--search', type=str, metavar='TV_SERIES', help='what to search for')
    return parser


def get_access_token():
    url = 'https://api.thetvdb.com/login'
    payload = {'apikey': 'FBOBJZQ4H8OEG8Q1'}
    response = requests.post(url, json=payload)
    return response


def get_refresh_token():
    """Try to get a refresh token, then return a response no matter what"""
    url = 'https://api.thetvdb.com/refresh_token'
    headers = {'Authorization': 'Bearer {}'.format(TOKEN)}
    print("Refreshing auth token")
    response = requests.get(url, headers=headers)
    return response


def save_token(response):
    with open('token.txt', 'w') as outfile:
        outfile.write(response.json()['token'])
        

def load_token():
    global TOKEN
    with open('token.txt', 'r') as infile:
        TOKEN = infile.read()


# curl command to search for series
# curl --header 'Content-Type: application/json' --header "Authorization: Bearer [TOKEN]" --request GET https://api.thetvdb.com/search/series?name=mythbusters

def find_series(search):
    url = 'https://api.thetvdb.com/search/series'
    payload = {'name': search}
    headers = {'Authorization': 'Bearer {}'.format(TOKEN)}
    response = requests.get(url, params=payload, headers=headers)
    return response


def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.search is not None:
        load_token()

# When a search receives a fail status, raise an exception and try to get a new
# access token. If that succeeds, save the token and perform the search again.
# Otherwise, try to get a new token again. 
        tries = 3
        for i in range(tries):
            try:
                response = find_series(args.search)
                response.raise_for_status()
            except HTTPError as e:
                if (i < tries - 1 and response.status_code == requests.codes.unauthorized):
                    response = get_access_token()
                    if response.status_code == requests.codes.ok:
                        save_token(response)
                        load_token()
                    continue
                else:
                    print(e)
                    sys.exit()
            break  # Don't retry when there is no exception

        try:
            results_list = response.json()['data']
        except KeyError as e:
            print("Did not receive a valid search result")
            print(e)
            sys.exit()
            
        for position, item in enumerate(results_list):
            print('[{selector}] {series_name}'.format(selector=position + 1, series_name=item['seriesName']))

        choice = input('Enter choice: ')

        # Catch exceptions for input that isn't a number, or isn't in the list of
        # results. Throw an exception if input isn't a positive number.
        try:
            chosen_integer = int(choice)
            if chosen_integer <= 0:
                raise ValueError
            chosen_result = results_list[chosen_integer - 1]
            print('You have selected "{}"'.format(chosen_result['seriesName']))
        except (ValueError, IndexError):
            print("Does not match any available choices")


if __name__ == "__main__":
    main()
