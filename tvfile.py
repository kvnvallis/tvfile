#!/usr/bin/env python3
#
# TODO:
#
# * Option to search by episode number, not title
# * Create different styles for filenames and make it easy to add new ones.
# * Write tests and learn how to run them


import sys
import os
import requests
import json
import argparse
import json
import string
import textwrap
import re
#import configparser

from glob import glob
#from requests.exceptions import HTTPError


# TOKEN is modified by load_token()
TOKEN = ''
CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.config', 'tvfile')
TOKEN_PATH = os.path.join(CONFIG_DIR, 'token.txt')


def create_parser():
    parser = argparse.ArgumentParser(
        description='Rename files with correct season and episode numbers according to the TheTVDB.com')
    parser.add_argument('-s', '--search', required=True, metavar='SERIES_NAME',
                        help='Search term to find the name of the tv series')
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-l', '--symlinks', metavar='DEST_DIR', help='Create renamed files as symlinks in a given directory')
    group.add_argument('-r', '--rename', action='store_true',
                       help='Rename original files in place')
    parser.add_argument('-m', '--multiple-episodes', action='store_const',
                        const=2, help='Use this flag when there are two episodes per file')
    parser.add_argument('files', nargs='+', metavar='EPISODE_FILES', help='The tv episode files to rename, intended to be used with shell expansion, e.g. *.mkv')
    parser.add_argument('--episode-numbers', action='store_true', help='Search for episodes by number instead of name. Useful when files are ordered correctly but the syntax is wrong.')
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
    with open(TOKEN_PATH, 'w') as outfile:
        outfile.write(response.json()['token'])


def load_token():
    global TOKEN
    try:
        with open(TOKEN_PATH, 'r') as infile:
            TOKEN = infile.read()
    except FileNotFoundError:
        # Create the empty file
        open(TOKEN_PATH, 'w').close()


# curl command to search for series
# curl --header 'Content-Type: application/json' --header "Authorization: Bearer [TOKEN]" --request GET https://api.thetvdb.com/search/series?name=mythbusters

def find_series(search):
    url = 'https://api.thetvdb.com/search/series'
    payload = {'name': search}
    headers = {'Authorization': 'Bearer {}'.format(TOKEN)}
    response = requests.get(url, params=payload, headers=headers)
    return response


def get_episodes(series_id, page=1):
    """Take integer or string values for the series id and the page of results, then return the response"""
    # There is a max of 100 results per page
    url = 'https://api.thetvdb.com/series/{}/episodes'.format(series_id)
    payload = {'page': '{}'.format(page)}
    headers = {'Authorization': 'Bearer {}'.format(TOKEN)}
    response = requests.get(url, params=payload, headers=headers)
    return response


def get_all_episodes(series_id):
    """Return all episodes in a list of json objects"""
    # When on page 2
    # {'first': 1, 'last': 4, 'next': 3, 'prev': 1}
    page = 1
    all_episodes = list()
    while True:
        episodes = get_episodes(series_id, page).json()
        if episodes['links']['next'] is not None:
            all_episodes = all_episodes + episodes['data']
            page = episodes['links']['next']
        else:
            all_episodes = all_episodes + episodes['data']
            return all_episodes


# These simple get/post functions are probably good candidates for decorators
def episode_info(episode_id):
    url = 'https://api.thetvdb.com/episodes/{}'.format(episode_id)
    headers = {'Authorization': 'Bearer {}'.format(TOKEN)}
    response = requests.get(url, headers=headers)
    return response


def list_choices(results_list):
    """Print out numerical selectors next to a list of choices. Argument must be a list of strings."""
    for position, item in enumerate(results_list):
        print('[{selector}] {series_name}'.format(
            selector=position + 1, series_name=item))


def select_choice(items):
    """Take the user's numerical selection and use it to get the corresponding item from a list. Return a selection of any type."""
    # Catch exceptions for input that isn't a number, or isn't in the list of
    # results. Throw an exception if input isn't a positive number.
    print('>>> Select a number or enter 0 for none')
    choice = prompt_user('Enter choice: ')
    try:
        chosen_integer = int(choice)
        if chosen_integer < 0:
            raise ValueError
        elif chosen_integer == 0:
            return None
        selection = items[chosen_integer - 1]
        return selection
    except (ValueError, IndexError):
        print("Does not match any available choices")


def prompt_user(prompt):
    while True:
        text = input(prompt).lower()
        if not text:
            continue
        else:
            return text


def remove_chars(words, characters):
    """Return a given string with given characters removed. Expects both arguments to be strings."""
    table = str.maketrans('', '', characters)
    return words.translate(table)


#def phrase_search():
#    pass


def search_titles(episode_titles, num_searches):
    """Accept a list of titles as an argument. Prompt the user for a search string and try to find an exact match, then search each word in the phrase. List the results and let the user choose the correct title. Return one or more chosen titles as a tuple."""
    chosen_episode_list = list()
    search_count = 0

    while (search_count < num_searches):
        text = prompt_user('Enter an episode title: ')

        # If you enter only punctuation, it will be stripped and the
        # resulting blank string will return all episodes as a possible
        # match.
        title_search = remove_chars(text, string.punctuation).lower()

        phrase_matches = [ep_title for ep_title in episode_titles if title_search in remove_chars(
            ep_title, string.punctuation).lower()]

        if phrase_matches:
            list_choices(phrase_matches)
            chosen_episode = select_choice(phrase_matches)
            if chosen_episode is None:
                continue
            chosen_episode_list.append(chosen_episode)
            search_count += 1
        else:
            broad_matches = keyword_search(
                title_search, episode_titles)
            if broad_matches:
                list_choices(broad_matches)
                chosen_episode = select_choice(broad_matches)
                if chosen_episode is None:
                    continue
                chosen_episode_list.append(chosen_episode)
                search_count += 1
            else:
                # Try the search again
                print("Couldn't find a match.")

    return tuple(chosen_episode_list)


def keyword_search(title, episodes):
    """Perform a broad search by checking each word in the search string against each word in the title. Take as arguments the episode title to search for and an iterable containing all episode titles."""
    # This is helpful when the search string contains an error, e.g.
    # spelling mistake. If you don't use a set(), this matches the same
    # title multiple times, and returns duplicate titles equal to the
    # number of words matched from the search string.
    words_in_title = title.split()
    broad_matches = set()
    for word in words_in_title:
        for episode_title in episodes:
            if word in remove_chars(episode_title, string.punctuation).lower().split():
                broad_matches.add(episode_title)
    broad_matches_list = list(broad_matches)
    return broad_matches_list


def expand_paths(files):
    """Take a list of files where some might contain a '*' and expand the paths, and return a complete list of files"""
    episode_files = list()
    for path in files:
        if '*' in path:
            expanded_paths = glob(path)
            for exp_path in expanded_paths:
                episode_files.append(exp_path)
        else:
            episode_files.append(path)
    return episode_files


def build_filename(series_name, season_number, episode_names, episode_numbers):
    """Accept names with words separated by spaces, and numbers as strings not integers. Return a filename without a file extension."""
    if len(season_number) < 2:
        season_number = '0' + season_number

    for index, ep_number in enumerate(episode_numbers):
        if len(ep_number) < 2:
            ep_number = '0' + ep_number
            episode_numbers[index] = ep_number

    season_episode_abbrev = 'S' + season_number + \
        'E' + '-E'.join(episode_numbers)
    series_name = series_name.replace(' ', '.')

    for index, ep_name in enumerate(episode_names):
        new_name = ep_name.replace(' ', '.')
        episode_names[index] = new_name

    filename_parts = [series_name,
                      season_episode_abbrev, '-'.join(episode_names)]

    illegal_chars = '<>:"/\|?*'
    new_filename = remove_chars(
        '.'.join(filename_parts), illegal_chars)
    return new_filename


def main():
    parser = create_parser()
    global args
    args = parser.parse_args()

    if not os.path.isdir(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

    # Use glob to expand file paths for compatibility with windows shells
    if os.name == 'nt':
        episode_files = expand_paths(args.files)
    else:
        episode_files = [
            filename for filename in args.files if os.path.exists(filename)]

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
            except requests.exceptions.HTTPError as e:
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
            series_list = response.json()['data']
        except KeyError as e:
            print("Did not receive a valid search result")
            print(e)
            sys.exit()

        series_titles = tuple([series['seriesName'] for series in series_list])
        list_choices(series_titles)
        series_data = select_choice(series_list)

        if series_data is None:
            print("No series selected, run the script again")
            sys.exit()

        print('You have selected "{}"'.format(series_data['seriesName']))
        series_id = series_data['id']
        episode_list = get_all_episodes(series_id)
        episode_titles = tuple([episode['episodeName']
                                for episode in episode_list])
                                
        episode_names_ids = dict()
        for episode_data in episode_list:
            episode_names_ids[remove_chars(
                episode_data['episodeName'], string.punctuation).lower()] = episode_data['id']

        # Collect season and episode numbers too, so that we have the
        # option to search by number instead of title

        episode_nums_ids = dict()
        for episode_data in episode_list:
            episode_nums_ids[str(episode_data['airedSeason']) + 'x' + str(episode_data['airedEpisodeNumber'])] = episode_data['id']
        #print(episode_nums_ids)

        if args.episode_numbers:
            print(">>> Episode numbers must be given in the format SEASONxEPISODE e.g. 3x6 for season 3 episode 6")

        if not args.multiple_episodes:
            num_searches = 1
        else:
            num_searches = args.multiple_episodes

        for filename in episode_files:
            print('Episode File: {}'.format(filename))

            if args.episode_numbers:
                given_episode_numbers = list()
                entry_count = 0
                while True:
                    # TODO: Make sure to validate input
                    episode_number = prompt_user('Enter episode number: ')
                    if re.compile("^\d{1,2}x\d{1,2}$").match(episode_number):
                        # Remove any leading zeroes
                        season_and_episode = [num.lstrip('0') for num in re.split('x', episode_number)]
                        episode_number = 'x'.join(season_and_episode) 
                        try:
                            episode_nums_ids[episode_number]
                        except KeyError:
                            print("Episode does not exist")
                            continue
                        given_episode_numbers.append(episode_number)
                        entry_count += 1
                    else:
                        print("Invalid entry, try again")
                        continue

                    if entry_count >= num_searches:
                        break

                episode_ids = [episode_nums_ids[ep_num] for ep_num in given_episode_numbers]
            else:
                chosen_episodes = [remove_chars(ep_name, string.punctuation).lower() for ep_name in search_titles(episode_titles, num_searches)]
                episode_ids = [episode_names_ids[ep_name] for ep_name in chosen_episodes]

            # END SEARCH SECTION / BEGIN RETRIEVING EPISODE DATA

            # This is an obvious candidate for a function, but the previous
            # code (for retrieving the tv series info) has an extra step where
            # it renews the access token upon failure. Decorators might also be
            # useful here.

            episode_data_list = list()
            for ep_id in episode_ids:

                tries = 3
                for i in range(tries):
                    try:
                        #response = episode_info(episode_names_ids[remove_chars(
                        #    chosen_episode, string.punctuation).lower()])
                        response = episode_info(ep_id)
                        response.raise_for_status()
                    except requests.exceptions.HTTPError as e:
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

            series_name = series_data['seriesName']
            # Just grab the last one in memory, for now
            season_number = str(episode_data['airedSeason'])
            episode_names = [data['episodeName'] for data in episode_data_list]
            episode_numbers = [str(data['airedEpisodeNumber']) for data in episode_data_list]

            new_filename = build_filename(series_name, season_number, episode_names, episode_numbers)
            file_extension = os.path.splitext(filename)[1]
            print('>>> Your new filename is "{}"'.format(
                new_filename + file_extension))

            filepath = os.path.abspath(filename)
            if args.symlinks and os.path.isdir(args.symlinks):
                linkpath = os.path.abspath(args.symlinks)
                os.symlink(filepath, os.path.join(
                    linkpath, new_filename + file_extension))
            elif args.rename:
                filedir = os.path.dirname(filepath)
                os.rename(filepath, os.path.join(
                    filedir, new_filename + file_extension))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('\n')
        sys.exit(0)

