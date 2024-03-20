# Strava Running Title/Description Automation - Guide

It is amazing you have decided to venture this far into this project to the point of using it yourself. Anyways, here is a guide on how to use this program yourself, assuming the setup has been completed as instructed.

Note: this guide cannot possibly every use case, so beware and experiment with the program or read the source code to have a better understanding of its logic.

## Input
The program relies on a JSON configuration file as input. The expected file is `data/config.json`, meaning the `data` sub-folder must be created for use alongside the corresponding file.

The input is non-trivial, and it is significantly simpler to rely on an example input file rather than explain every tiny detail, although most details will be covered anyways. Check out the `example_config.json` file for a sample configuration file you can directly copy and edit for your own use case.

### Configuration Schema
- `client_id` (integer) - the **client ID** of the Strava app that you plan to use this program with.
- `client_secret` (hex string) - the **client secret** of the same Strava app.
- `refresh_minutes` (integer) - the number of **minutes per scan** of the past few activities for runs i.e. how often the program fetches activites, processes them and renames them if appropriate. Must be in the range [2, 60]. The shorter this duration, the greater the granularity, but the more API calls are needed. If this setting is not provided, the default is 5 minutes.
- `hr_zones` - an optional dictionary storing the **threshold heart rate** for each heart rate zone, in beats per minute (must be integers). Heart rate zones go from 1 to 5. Hence, the threshold HR for each zone from 1-5 must be set like seen in the example (increasing for each zone). This field is optional but will be needed if you wish to embed heart rate zone information in the text.
- `markers` - a major field that allows various activity **metrics** to be able to be interpreted and **mapped to a title/description string** based on a **target range or value**. Importantly, these strings are not necessarily the entire title/description and instead are more likely to be **combined**, alongside hard-coded parts. It will make more sense once the specific examples are discussed.
    - `distance` - interprets the **distance** of the run in **kilometres**. Sub-markers are created that take the activity's distance and maps it to a string based on the range.
        - Each sub-marker is an array containing sub-arrays, each of which is **length 4** and the values mean the following:
        **[min_distance, max_distance, title, description]**.
        - For the example `category` key, the following is the meaning of each sub-array:
            - The first array matches distances in the range **[0, 5), not including exactly 5km**. If the distance is in that range, if selecting a title, 'Short' will be selected, and if selecting a description, 'Under 5k' will be selected.
            - The second array matches distances in the range [5, 10) with the same logic as above.
            - The third array has the same logic.
            - The fourth array is somewhat different. The **null as the second value implies no upper bound**. It also introduces another feature - the title and description field can be an **array of strings** - where if the interval is matched, a **random** title/description is selected, allowing for **variety** and not the exact same text generated each time.
        - **Multiple** sub-markers can be created.
    - `moving_time` - interprets the **moving time** of the run in **seconds**. Moving time is how long you were **active** during the run. It works in the exact same way as `distance`, except the metric is different - moving time in seconds.
    - `elapsed_time` - interprets the **elapsed time** of the run in **seconds**. Elapsed time is the **duration** from start to finish regardless of pauses or stops. Logically, it is greater than or equal to moving time. This field works in the same way as both `distance` and `moving_time`.
    - `pace` - interpets the **average pace** of the run in seconds per kilometre. For example, a pace of 5:00/km is equal to 300 in this program. This program bases pace on the **moving time**, not elapsed time, just like Strava does by default. It works generally in the same way as the other metrics so far except some more unusual yet accepted sub-arrays have been shown in the `example` key:
        - The first sub-array matches paces in the range 6:00/km and 10:00/km, with the title of 'Chill'. However, the description field is set to **null**, meaning **no description is available** for this interval. Hence, the sub-array only provides a title.
        - The second sub-array works similarly except title is set to null instead, which similarly means the sub-array only provides a description.
        - The third sub-array is very unusual since it has **two null** values to start with. This means it is a **fallback** (like 'else'), meaning it is used if the pace is not in range of the other intervals. Also in this case, this array is only of length 3, where **description can be omitted and is null by default** (similar to the first sub-array).
    - `start_time` - the **local start time** of the run in **HHMM** format. This is slightly different in the fact that numbers are not involved in the range for the first time. Note the strict use of the 24-hour HHMM format to represent the times. Here is an explanation of the `time_of_day` key:
        - The first sub-array indicates that for runs that started at 5am or after but before 8am will have the corresponding title/description.
        - The second sub-array matches runs that started in the range [8am, 12am). Note the **empty** description string, which is valid.
        - The final sub-array matches runs that started at 11pm or later, but before 5am (the next day of course). Indeed, **crossing over midnight** is acceptable.
    - `dates` - the **local start date** of the run in **YYYY-MM-DD** format, with powerful **asterisk wildcards**. This is slightly different because a direct match rather than a range match is involved, so **3-arrays** are used instead of 4-arrays. The `dates` key provides useful examples:
        - The first sub-array matches all runs that started on Christmas Day (25th December) regardless of year.
        - The second sub-array matches all runs that started on 29th February regardless of year.
        - The third sub-array matches all runs that started on the 1st day of any month.
        - The fourth sub-array contains null for the date meaning it is a fallback. In this case, both the title and description strings are empty as there is nothing significant to mention.
    - `elevation` - the **total elevation** of the activity in **metres**. Works in the same way as the other numeric metrics.
    - `elevation_per_km` - the **mean elevation per kilometre** in **metres**, better when gauging the overall hilliness of the run rather than blindly considering the total elevation. Works in the same way as the other numeric metrics.
    - `cadence` - the number of **steps taken per minute** during the run. Works in the same way as other numeric metrics.
    - Additionally, it is possible for a particular metric in a run to fall into **multiple** ranges or match multiple date strings, in which case a **random interval/record with an available title/description** will be selected and its title/description string used accordingly. Failure will occur if no matches occur with an available title/description as required, discussed more in a moment.
- `templates` - an array of templates that, at last, provide semantics on how to generate the title/description. A suitable template is selected that can be used to generate the title and description of a run. Each template dictionary has the following fields:
    - `title` - the **title string** (or an **array** of title strings).
        - A title string allows **interpolation** of marker strings in **curly brackets**, alongside a constant format weather or heart rate zones string.
        - The following is a valid title string in the example file: "{start_time.time_of_day} {distance.category} {date.dates} Run". Here, a suitable `time_of_day` title string is selected from the `start_time` metric, a suitable `category` title string from the `distance` metric is selected, and a suitable `dates` title string from the `date` metric is selected (which may be empty as seen and therefore have no effect). For example, a run with start time 1100, a distance 11.5km and date 2024-12-25 would have the following title: *Morning Long Christmas Run*.
        - An array of title strings allows for **multiple** attempts and fallbacks in case the first title string and beyond do not work for a particular run.
        - If a title is unavailable for any of the placeholders in curly brackets, either another title string in the array must be used if possible (starting from the first and sequentially trying each title string until success), otherwise if the end of the array is reached or the single provided title string is invalid, unfortunately, the **template cannot be used**.
    - `description` - the description string (or array of description strings).
        - Works in the **same** way as the title string in general.
        - The example description string introduces two additional placeholders `weather` and `hr_zones`.
            - `weather` provides weather information on the run based on **another project's data collection**: https://github.com/leoz0214/BBC-Weather-Automation. It relies on available data from this project's database for a suitable hourly recording in a nearby location of the run (within 20 kilometres). It is recommended to unfortunately avoid using this powerful placeholder unless you fully know how it works, and how to adjust the code for it to work in your personal scenario. Included weather information includes:
                - Temperature/Feels like temperature (°C)
                - Weather type (sunny, rainy etc.)
                - Wind speed (mph) and direction (16-point direction)
                - Humidity (%)
                - Pressure (mb)
                - Visibility (good, poor etc.)
            - `hr_zones` provides information on the time spent in **zones 1 to 5** and the corresponding percentages. It relies on the heart rate zones to be input in this file and the run to have **heart rate data**.
    - `priority` - an integer determining the priority of a template. Templates with the **smallest integer** of priority will be tried **first** before resorting to the increasing integers. This is also optional and will cause minimum priority (tried last, after any templates with explict priority).
    - `restriction` - an optional further set of rules that narrows down the usage of this template for runs that meet certain **criteria** only:
        - `distance` - only accept runs that fall in a **distance interval** (km), as a **2-array** [min_distance, max_distance] (inclusive), or in any intervals in an **array of 2-arrays** (for non-continuous ranges).
        - `pace` - same as distance but for pace (seconds per kilometre).
        - `start_time` - same as the others but for start time (HHMM string).
- `route_template` - an extension to the standard templates detailed above but with the additional feature of listing a set of **latitude/longitude points** that must be reached during the run, and a blacklist of points that must not be reached during the run. Route templates have separate priority values, but are always tried before ordinary templates. The only differences between route templates and ordinary templates are:
    - `points` - an **array of latitude/longitude points** that the **run must cover** for the route to be matched. A single lat/long point during the run that reaches a point suffices as touching an input point. The format is **[latitude, longitude, radius]**, where radius is an optional third value to specify the acceptable **margin of error** in metres (since GPS recordings are imperfect). The default radius is 25 metres.
    - `restrict.blacklist` - an additional restriction that specifies an **array of latitude/longitude points** that absolutely **must not be reached** during the run, otherwise the route template will not be used. Otherwise, it works similarly to `points`.

This is a detailed yet slightly ambiguous overview of the complex input of the program. **Flexibility is prioritised over ease of use**. Advanced users may read the source code for a more comprehensive understanding. But hopefully the example config file provides a solid overview of how the input works.

## Running the Program
Provided the `data/config.json` file has been correctly filled in, you are hopefully ready to start using the program.

Simply run the `strava.py` top-level script as usual, and the program should begin running smoothly if everything works correctly.

Here is a high-level overview of the program's logic per iteration - explore the source code for a full understanding (or simply read `src/main.py` for an overview):
- The **configuration file is loaded and thoroughly validated**, raising an error if the input is invalid, with a description of the problem.
- The Strava API **access token is loaded**.
    - If there is no access token available (e.g. first time running the program), the OAuth flow occurs, which requires a web browser to complete. If you plan to use a headless cloud server to run the program, make sure to perform one-time OAuth on a device with a browser and copy the credentials file into the required location.
    - If a previous access token is found, if within 10 minutes of expiry, it is automatically renewed, otherwise it can be used again.
- The **last 5 activities are queried** with IDs returned:
    - Seen activtity IDs are recorded by the program such that activities are only processed by the program once.
    - If an activity has already been seen by the program before, it is ignored.
    - Otherwise, fetch and return detailed data for the activity (including location and HR streams) and return it as a potential candidate for title/description generation.
- **Each new activity is processed** like so:
    - If the **title** of the activity is **not default** i.e. Morning Run, Lunch Run, Afternoon Run, Evening Run or Night Run, or if the **description is set**, the activity title/description has already been manually modified so will not be touched by the program (manual over machine). The processing for the current activity terminates.
    - An attempt is made to generate a title and description for the activity given its data and the configuration data.
        - **Route templates are tried first** in priority order as mentioned in the configuration section.
        - Ordinary templates are tried after, again in priority order.
        - The activity must first pass the template restrictions and then be able to have a title and description generated from the template. Upon success, the title and description are returned.
    - If the title and description are successfully generated, the program makes an API call to update the activity's title and description. Success!
    - Otherwise if title/description generation fails i.e. no suitable templates, then the activity is skipped.
- **Time is waited** until the current iteration has taken the number of minutes as set in the `refresh_minutes` option.

Setting up this program on a cloud server is one way of keeping it running non-stop. This is beyond the scope of this guide

## Relevant Files
This program has several external files associated with it. These are seen in the `src/const.py` file and can be modified if desired.

- `data/config.json` - **input configuration file** as already mentioned.
- `data/log.log` - the **output log file** highlighting successes, warnings and errors. Logging occurs both live in the console and into this file. It is possible to view this file to know what failed, and when it failed.
- `_credentials.json` - the **credentials file** containing the access token and related data (expiry date). It should not be modified directly or else the program may malfunction. However, it can of course be moved from one environment to another - such as generating the file locally through OAuth and subsequently using it on the cloud.
- `_seen_activities.txt` - stores a **list of activity IDs** on new lines, representing activities that have **already been seen** by the program and are not to be re-processed. However, it is possible to safely remove activity IDs from the list in case you wish to re-process it anyways for whatever reason. Moving this file is also suitable.
- Weather Database - this is a path to the **weather database in another project**. The path seen in the source is my personal circumstances for this, not directly linked to this program. If you are interested in being able to use this weather feature in this project, set up the project and set the path to the database of the weather program. For details, consult: https://github.com/leoz0214/BBC-Weather-Automation.
- `geo.dll` - the **C++ Windows shared library binary for fast point matching**. A list of points is taken (the points or blacklist for a route template) alongside a list of the latitude/longitude points of the activity, and either all points are checked to be reached by at least 1 latitude/longitude co-ordinate, or no points by touched by any latitude/longitude co-ordinate. This is written in C++ since the algorithm can become slow in Python for larger lists of either type (quadratic time complexity), whereas C++ completes this by a large constant factor faster.
- `geo.so` - the **Linux** equivalent of `geo.dll`.

Note, the shared libraries are not mandatory, equivalent Python code will be run if unavailable, which is fast enough for normal data.

## Source Code
The Python/C++ source code is evident in the `src` folder. Code has been organised into sensible modules. Feel free to explore/modify the code, which has been documented to an extent and is structured reasonably overall.

List of modules in `src`:
- `activity.py` - fetches recent activities and activity details/streams.
- `api.py` - Strava API interface including OAuth authentication.
- `configure.py` - loads and meticulously validates the configuration file.
- `const.py` - contains useful constants, mainly file paths.
- `generate.py` - generates a title/description given the config and activity data.
- `geo.cpp` - C++ implementation of the point matching as mentioned already. Compiled using g++ as a static shared library with -O2 optimisation.
- `main.py` - main module - holds the main program loop.
- `utils.py` - general utility functions for the program.
