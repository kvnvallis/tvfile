#!/usr/bin/env python

import sys
import requests
import json
import argparse
import json
import string

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


def get_episodes(series_id):
    url = 'https://api.thetvdb.com/series/{}/episodes'.format(series_id)
    headers = {'Authorization': 'Bearer {}'.format(TOKEN)}
    response = requests.get(url, headers=headers)
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
        except (ValueError, IndexError):
            print("Does not match any available choices")

        series_data = results_list[chosen_integer - 1]
        print('You have selected "{}"'.format(series_data['seriesName']))

        series_id = series_data['id']
        episode_list = get_episodes(series_id).json()['data']

        # Collect ids and names in a list of tuples
        #id_episode_names = list()
        #for episode_data in episode_list:
        #    id_episode_names.append(
        #        (episode_data['id'], episode_data['episodeName'].lower()))

        # Used as argument to translate() to remove punctuation from titles
        table = str.maketrans('', '', string.punctuation)

        # Make a dictionary of (sanitized) episode titles to episode IDs
        episode_names_ids = dict()
        for episode_data in episode_list:
            episode_names_ids[episode_data['episodeName'].lower().translate(table)] = episode_data['id']

        for k, v in episode_names_ids.items():
            print(episode_names_ids)

        # Make user input lowercase then remove punctuation and split words into a list
        text = input('Enter an episode title: ').lower()
        title = text.translate(table)
        words_in_title = title.split()
        #print(words_in_title)

        # First try to match the whole search string to a title. 
        phrase_matches = list()
        for episode_name in episode_names_ids:
            if title in episode_name:
                phrase_matches.append(episode_name)
        if phrase_matches:
            print(phrase_matches)
        # Perform a broad search by checking each word in the search string
        # against each word in the title. This is helpful when the search
        # string contains an error, e.g. spelling mistake. If you don't use a
        # set(), this matches the same title multiple times, and returns
        # duplicate titles equal to the number of words matched from the search
        # string. 
        else:
            broad_matches = set()
            for word in words_in_title:
                for episode_name in episode_names_ids:
                    if word in episode_name:
                        broad_matches.add(episode_name)
            print(broad_matches)

        # This will of course only show exact matches
        #if name in episode_names:
        #    print("Wow we found your episode")

        # Slightly better partial string search
        #matches = list()
        #for name in episode_names:
        #    if name.find(title) >= 0:
        #        matches.append(name)

        #print('\n'.join(episode_names))
        #print(json.dumps(episode_list.json(), indent=4, sort_keys=True))


if __name__ == "__main__":
    main()
