#!/usr/bin/env python3
#
# TODO: 
#
# * Create different styles for filenames and make it easy to add new ones.
# Handle shows that go by year instead of season (like mythbusters). Clean up
# with autopep8 before making another commit.
#
# * My Ubuntu server's `python` binary is version 2.7. Should you change
# `python` to `python3` at the top of the script?
#
# * If `token.txt` doesn't exist in the current directory, the script crashes.
# Create token.txt at a reasonable location if it doesn't exist (the current
# directory is the wrong place). 

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
    parser.add_argument('--search', required=True, help='what to search for')
    parser.add_argument('--multiple-episodes', action='store_const', const=2, help='Use when there are two episodes per file')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--symlinks', help='create renamed files as symlinks in a given directory')
    group.add_argument('--in-place', action='store_true', help='rename files in-place')
    parser.add_argument('files', nargs='+', help='the tv files to rename')
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


def prompt_user(prompt):
    while True:
        #text = input('Enter an episode title: ').lower()
        text = input(prompt).lower()
        if not text:
            print("You left the field blank. Try again.")
        else:
            return text


def phrase_search():
    pass


def keyword_search(title, episodes):
    """Perform a broad search by checking each word in the search string against each word in the title. Take as arguments the episode title to search for and an iterable containing all episode titles."""
    # This is helpful when the search string contains an error, e.g.
    # spelling mistake. If you don't use a set(), this matches the same
    # title multiple times, and returns duplicate titles equal to the
    # number of words matched from the search string. 
    words_in_title = title.split()
    broad_matches = set()
    for word in words_in_title:
        for episode_name in episodes:
            if word in episode_name.split():
                broad_matches.add(episode_name)
    broad_matches_list = list(broad_matches)
    return broad_matches_list


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
                        # You might want to get a refresh token here; They last longer
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

            if not args.multiple_episodes:
                num_searches = 1
            else:
                num_searches = args.multiple_episodes

            chosen_episode_list = list()
            search_count = 0
            while (search_count < num_searches):
                text = prompt_user('Enter an episode title: ')
                                    
                # If you enter only punctuation, it will be stripped and the
                # resulting blank string will return all episodes as a possible
                # match.
                title = text.translate(table)

                # First try to match the whole search string to a title. 
                phrase_matches = [ep_name for ep_name in episode_names_ids if title in ep_name]

                if phrase_matches:
                    list_choices(phrase_matches)
                    chosen_episode = select_choice(phrase_matches)
                    chosen_episode_list.append(chosen_episode)
                    search_count += 1
                else:
                    broad_matches = keyword_search(title, episode_names_ids)
                    if broad_matches:
                        list_choices(broad_matches)
                        chosen_episode = select_choice(broad_matches)
                        chosen_episode_list.append(chosen_episode)
                        search_count += 1
                    else:
                        # Try the search again
                        print("Couldn't find a match.")  


            ### END SEARCH SECTION / BEGIN RETRIEVING EPISODE DATA

            # This is an obvious candidate for a function, but the previous
            # code (for retrieving the tv series info) has an extra step where
            # it renews the access token upon failure. Decorators might also be
            # useful here.

            episode_data_list = list()
            for chosen_episode in chosen_episode_list:

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
                episode_data_list.append(episode_data)
                #print(json.dumps(episode_data, indent=4))

            series_name = series_data['seriesName'].replace(' ', '.')
            season_number = str(episode_data['airedSeason'])  # Just grab the last one in memory, for now
            if len(season_number) < 2:
                season_number = '0' + season_number

            episode_names = [data['episodeName'].replace(' ', '.') for data in episode_data_list]

            episode_numbers = list()
            for data in episode_data_list:
                ep_number = str(data['airedEpisodeNumber'])
                if len(ep_number) < 2:
                    ep_number = '0' + ep_number
                episode_numbers.append(ep_number)

            season_episode_abbrev = 'S' + season_number + 'E' + '-E'.join(episode_numbers)

            filename_parts = [series_name, season_episode_abbrev, '-'.join(episode_names)]  # Only use the first episode name
            new_filename = '.'.join(filename_parts)
            file_extension = os.path.splitext(filename)[1]
            print('Your new filename is "{}"'.format(new_filename + file_extension))

            filepath = os.path.abspath(filename)
            if args.symlinks and os.path.isdir(args.symlinks):
                linkpath = os.path.abspath(args.symlinks)
                os.symlink(filepath, os.path.join(linkpath, new_filename + file_extension)) 
            elif args.in_place:
                filedir = os.path.dirname(filepath)
                os.rename(filepath, os.path.join(filedir, new_filename + file_extension)) 


if __name__ == "__main__":
    main()
