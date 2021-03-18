# tvfile

tvfile assists you in renaming your tv shows so that the files conform to theTVDB.com and media managers like plex and kodi. User input is required for each episode file. The script does not currently try to guess episode titles or numbers based on the filename. Windows and Linux versions are available for command line use only.


## Downloads

__tvfile v0.2-alpha:__

* [Ubuntu 16.04+ (64-bit)](https://github.com/kvnvallis/tvfile/releases/download/v0.2-alpha/tvfile)

__tvfile v0.1-alpha:__

* [Windows XP/7/10 (32-bit)](https://github.com/kvnvallis/tvfile/releases/download/v0.1-alpha/tvfile.exe)
* [Ubuntu 16.04+ (64-bit)](https://github.com/kvnvallis/tvfile/releases/download/v0.1-alpha/tvfile)


## Installation

Copy tvfile to a location in your PATH.

    sudo cp '~/Downloads/tvfile' /usr/local/bin/
    sudo chown $USER /usr/local/bin/tvfile
    sudo chmod u+x /usr/local/bin/tvfile


## Output of `tvfile -h`

    Rename files with correct season and episode numbers according to the
    TheTVDB.com

    positional arguments:
      EPISODE_FILES         The tv episode files to rename, intended to be used
                            with shell expansion, e.g. *.mkv

    optional arguments:
      -h, --help            show this help message and exit
      -s SERIES_NAME, --search SERIES_NAME
                            Search term to find the name of the tv series
      -l DEST_DIR, --symlinks DEST_DIR
                            Create renamed files as symlinks in a given directory
      -r, --rename          Rename original files in place
      -m, --multiple-episodes
                            Use this flag when there are two episodes per file
      -n, --episode-numbers
                            Search for episodes by number instead of name. Useful
                            when files are ordered correctly but the syntax is
                            wrong.
      --style STYLE         Override style=name option from config
      --start-at START_AT   Start at the nth file in the list. Useful if script
                            exits early and you need to run the same command
                            again, resuming from where it previously left off.


## Examples

Create symlinks in your media library for episodes in your downloads folder.

    tvfile -s 'cowboy bebop' -l '/media/library/cowboy bebop/' '~/downloads/Cowboy Bebop Complete Series/*.mkv'

Rename files in-place without creating links.

    tvfile -s 'adventure time' -r '/media/library/adventure time/season 5/*.mkv' 
Rename files that contain 2 episodes per file.

    tvfile -s 'flapjack' -r -m '/media/library/flapjack/*.mkv'

Rename files by providing the episode number instead of searching for the episode title.

    tvfile -s 'samurai champloo' -r -n '/media/library/samurai champloo/*.mkv'


## Tips

* Hit ctrl-c to stop the script at any time
* Resume from previous file using `--start-at`
* You can enter search strings for episode names instead of the full title
* A token for TheTVDB.com API is stored in your user folder at `~/.config/tvfile/`
