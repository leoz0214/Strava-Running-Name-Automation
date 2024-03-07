# Strava Running Title/Description Automation

I enjoy running regularly, and have done so for as long as I have been programming. Strava is a powerful app for athletes to post activities in a simple, effective way. However, the default titles provided lack depth, simply the time of day followed by the sport type. The description is also empty by default.

This project aims to automate the title and descriptions of new runs that are detected using the Strava API. An input file is taken, and titles and descriptions can be deduced using a set of rules concerning activity distance, duration, date/time and even route.

In an ideal world, these features will have been successfully implemented after some passionate development on this project (very high level overview):
- Configuration JSON file with API credentials, markers, title/description templates and a few other settings. Thorough validation will be included for good practice in a vital skill.
- Regular API calls to check for new running activities.
- Fetching run data and generating a title/description, selecting a matching template.
- API call to update the title/description of the activity on Strava.

NOTE:  The project uses a personal Strava API account to run, and API credentials will obviously not be shared. It is for demonstration of various programming skills. The project will eventually be run on the cloud for personal use, so a CLI will be developed only. But if this project gets popular enough and there is enough encouragement, I may consider extending this project to a web app which can then have several users with a nice web interface, for general use for many runners.