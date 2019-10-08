#!/usr/bin/env python
#
# TODO: Present the user with matching episode titles and have her select which
# one is correct. Once selected, get the episode ID from the episode_names_ids
# dictionary, and look up the episode details with episode_info(). Collect the
# proper season number, episode number, and title. Then print it out to the
# screen (in preparation for actually renaming the file).


import sys
import os
import requests
import json
import argparse
import json
import string
import textwrap

from requests.exceptions import HTTPError


# Modified by load_token() 
TOKEN = ''


def create_parser():
    parser = argparse.ArgumentParser(description='Rename files according to tvdb')
    parser.add_argument('--search', required=True, type=str, metavar='TV_SERIES', help='what to search for')
    parser.add_argument('files', nargs='+', type=str, metavar='EPISODES', help='episode files')
    return parser


def get_access_token():
    print("Getting new access token...")
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


# These simple get/post functions are probably good candidates for decorators
def episode_info(episode_id):
    url = 'https://api.thetvdb.com/episodes/{}'.format(episode_id)
    headers = {'Authorization': 'Bearer {}'.format(TOKEN)}
    response = requests.get(url, headers=headers)
    return response


def list_choices(results_list):
    """Print out numerical selectors next to a list of choices. Argument must be a list of strings."""
    for position, item in enumerate(results_list):
        print('[{selector}] {series_name}'.format(selector=position + 1, series_name=item))


def select_choice(items):
    """Take the user's numerical selection and use it to get the corresponding item from a list. Return a selection of any type."""
    # Catch exceptions for input that isn't a number, or isn't in the list of
    # results. Throw an exception if input isn't a positive number.
    choice = input('Enter choice: ')
    try:
        chosen_integer = int(choice)
        if chosen_integer <= 0:
            raise ValueError
        selection = items[chosen_integer - 1]
    except (ValueError, IndexError):
        print("Does not match any available choices")
        sys.exit()
    return selection


def main():
    parser = create_parser()
    args = parser.parse_args()

    episode_files = [filename for filename in args.files if os.path.exists(filename)]

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
                        # You might want to get a refresh token here
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
            
        # List choices for tv series selection
        #for position, item in enumerate(results_list):
        #    print('[{selector}] {series_name}'.format(selector=position + 1, series_name=item['seriesName']))

        series_names = [series['seriesName'] for series in results_list]
        list_choices(series_names)
        series_data = select_choice(results_list)
        print('You have selected "{}"'.format(series_data['seriesName']))

        series_id = series_data['id']
        episode_list = get_episodes(series_id).json()['data']

        # Used as argument to translate() to remove punctuation from titles
        table = str.maketrans('', '', string.punctuation)

        # Make a dictionary of (sanitized) episode titles to episode IDs
        episode_names_ids = dict()
        for episode_data in episode_list:
            episode_names_ids[episode_data['episodeName'].lower().translate(table)] = episode_data['id']

        # Print out all the episodes for your own reference
        #ep_names = '; '.join(ep_name for ep_name in episode_names_ids.keys())
        #print(textwrap.fill(ep_names))

        # Display the current filename
        for filename in episode_files:
            print('Episode File: {}'.format(filename))

            # Make user input lowercase then remove punctuation and split words into a list.
            while True:
                text = input('Enter an episode title: ').lower()
                if not text:
                    print("You left the episode title blank. Try again.")
                else:
                    break  # Stop prompting for input
                
            title = text.translate(table)
            words_in_title = title.split()

            # First try to match the whole search string to a title. 
            phrase_matches = [ep_name for ep_name in episode_names_ids if title in ep_name]

            if phrase_matches:
                list_choices(phrase_matches)
                chosen_episode = select_choice(phrase_matches)

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
                        if word in episode_name.split():
                            broad_matches.add(episode_name)
                if broad_matches:
                    list_choices(broad_matches)
                    chosen_episode = select_choice(broad_matches)
                else:
                    # TODO: Program the option to skip episode or try the
                    # search again. Presently it just skips it.
                    print("Couldn't find a match.")  
                    continue  # Skip getting episode info

            # This is an obvious candidate for a function, but the previous
            # code (for retrieving the tv series info) has an extra step where
            # it renews the access token upon failure. Decorators might also be
            # useful here.
            tries = 3
            for i in range(tries):
                try:
                    response = episode_info(episode_names_ids[chosen_episode])
                    response.raise_for_status()
                except HTTPError as e:
                    if (i < tries - 1):
                        print("Retrying...")
                        continue
                    else:
                        print(e)
                        sys.exit()
                break

            episode_data = response.json()['data']
            print(json.dumps(episode_data, indent=4))
            season = episode_data['airedSeason']
            episode_number = episode_data['airedEpisodeNumber']
            episode_name = episode_data['episodeName']
            # Now just construct a filename out of those 3 things



if __name__ == "__main__":
    main()
