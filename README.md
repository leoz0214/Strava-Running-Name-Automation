# Strava Running Title/Description Automation

## Introduction
I enjoy running regularly, and have done so for as long as I have been programming. Strava is a powerful app for athletes to post activities in a simple, effective way. However, the default titles provided lack depth, simply the time of day followed by the sport type. The description is also empty by default.

## Solution
This project aims to automate the title and descriptions of new runs that are detected, using the Strava API. An input configuration file is taken, and titles and descriptions can be deduced using a set of rules concerning activity distance, duration, date/time and even route, alongside other metrics.

After effective developement, a robust command line solution has been implemented, with the following features:
- Configuration JSON file with API credentials, markers, title/description templates and a few other settings. Thorough validation will be included for good practice in a vital skill.
- Regular API calls to check for new running activities.
- Fetching and processing run data and generating a title/description, selecting a matching template.
- API call to update the title/description of the activity on Strava.

## Using the Program
Whilst the program is not designed to be generally used, it is still possible to use it if you are very eager to do so. Note that the setup will not be simplified due to the lack of expectation of usage. No EXE will be generated, and the program will need to be run directly through Python.

It is obviously assumed that you have an existing Strava account. Also remember that this program works for runs only, not cycles or other activity types.

Warning: The program is not simple to use, particularly in terms of input. This is to maximise its flexibility. 

Setup Requirements:
- The program has been designed to work on Windows and Linux. There is no reason it should not work on MacOS, but this has not been confirmed.
- Ensure you create your own Strava Application for this program. This is needed because this project relies on the Strava API which is on a per-app basis. Start here: https://developers.strava.com/. Note the client secret and client ID when successful.
- Ensure you have Python 3.10 or above installed.
- Install the required 3rd party libraries in the `requirements.txt` file using pip as usual. See the comments as to why the libraries are included.
- Download and extract the ZIP file in the Release section of this repository.
- The program can then be run using the `strava.py` file. But do not run it until it has been set up correctly, which will be explained in the guide.

Assuming the steps above have ben followed, consult the [guide](GUIDE.md) to know how to use this program.

## Disclaimer
The project uses a personal Strava API account to run, and API credentials will obviously not be shared. It is for demonstration of various programming skills and just the concept. The project is to be run on the cloud for personal use, so a CLI has be developed only. But if this project gets popular enough and there is enough encouragement, I may consider extending this project to a web app which can then have several users with a nice web interface, for general use for many runners. Let me know if you are interested in further development of this project, and I will certainly consider it, perhaps scaling it to a more user-friendly app/website.

The program is nothing without a Strava Application. For more details, refer to: https://developers.strava.com/.

Despite only being a personal project, the code in this repository has been made public and therefore is free to use for your own purposes. However, there will be no liability for any damages caused by usage of this code. 