from __future__ import print_function
import time
import cfbd
from cfbd.rest import ApiException
from pprint import pprint
import openai
import folium
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import pandas as pd
from collections import Counter

from flask import Markup
from flask import Flask, request, render_template
app = Flask(__name__)

global_map_html = ""

load_dotenv()

# setup the flast routing for the home page
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/map')
def map():
    global global_map_html
    return global_map_html

# Route responses back to the HTML after a get call from HTML
@app.route('/get')
def get_bot_response():
    user_input = request.args.get('msg')  # Get data from input field
    response = run_conversation(user_input)  # Pass user_input to run_conversation
    return json.dumps({
        "llm_response": response['llm_response'],
        "html_response": response['html_response']
    })



# Configure API key authorization: ApiKeyAuth
configuration = cfbd.Configuration()
configuration.api_key['Authorization'] = os.getenv('CFBD_API_KEY')
configuration.api_key_prefix['Authorization'] = 'Bearer'

openai.api_key = os.getenv('OPENAI_API_KEY')

# create an instance of the API classes
games = cfbd.GamesApi(cfbd.ApiClient(configuration))
conferences_api = cfbd.ConferencesApi(cfbd.ApiClient(configuration))
RankingsAPI = cfbd.RankingsApi(cfbd.ApiClient(configuration))
TeamsAPI = cfbd.TeamsApi(cfbd.ApiClient(configuration))

# Fetch the list of valid conferences to feed into the enum for the get_list_of_cfb_games function
valid_conferences = [conference.name for conference in conferences_api.get_conferences()]
#print(f"Valid conferences: {valid_conferences}")

import pandas as pd
from datetime import datetime

import pandas as pd
from datetime import datetime

def get_team_matchup_history(team1, team2, min_year=1869, max_year=None):
    print(f"Getting matchup history for {team1} vs {team2} from {min_year} to {max_year}")
    try:
        args = {k: v for k, v in {"min_year": min_year, "max_year": max_year}.items() if v is not None}
        matchup_history = TeamsAPI.get_team_matchup(team1, team2, **args)
        matchup_history = matchup_history.to_dict()  # Convert the TeamMatchup object to a dictionary

        # Convert the games list to a DataFrame
        games_df = pd.DataFrame(matchup_history['games'])

        # Calculate summary statistics
        win_counts = games_df['winner'].value_counts()
        games_df['win_diff'] = games_df['home_score'].sub(games_df['away_score']).abs()
        max_win_diff_game = games_df.loc[games_df['win_diff'].idxmax()]
        max_win_diff = max_win_diff_game['win_diff']
        max_win_diff_details = f"{max_win_diff_game['home_team']} {max_win_diff_game['home_score']} - {max_win_diff_game['away_team']} {max_win_diff_game['away_score']} on {datetime.strptime(max_win_diff_game['_date'], '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%b %d, %Y')}"

        def longest_streak(s):
            return (s != s.shift()).cumsum()[s].value_counts().max()

        games_df['team1_streak'] = games_df['winner'].eq(team1).groupby((games_df['winner'].eq(team1) != games_df['winner'].eq(team1).shift()).cumsum()).transform('count') * games_df['winner'].eq(team1)
        games_df['team2_streak'] = games_df['winner'].eq(team2).groupby((games_df['winner'].eq(team2) != games_df['winner'].eq(team2).shift()).cumsum()).transform('count') * games_df['winner'].eq(team2)

        longest_streak_team1 = games_df['team1_streak'].max()
        longest_streak_team2 = games_df['team2_streak'].max()

        longest_streak_team1_years = games_df.loc[games_df['team1_streak'] == longest_streak_team1, 'season'].agg(['min', 'max']).tolist()
        longest_streak_team2_years = games_df.loc[games_df['team2_streak'] == longest_streak_team2, 'season'].agg(['min', 'max']).tolist()     
        
        ties = len(games_df[games_df['winner'].isna()])



        # Prepare the HTML response
        html_response = f"<h2>History of the {team1} vs {team2} series from {min_year} to {max_year}</h2>"
        html_response += f"<p>Total wins: {team1} - {win_counts.get(team1, 0)}, {team2} - {win_counts.get(team2, 0)}, Ties - {ties}</p>"
        html_response += f"<p>Largest win differential: {max_win_diff} ({max_win_diff_details})</p>"
        html_response += f"<p>Longest win streak: {team1} - {longest_streak_team1} ({longest_streak_team1_years[0]} to {longest_streak_team1_years[1]}), {team2} - {longest_streak_team2} ({longest_streak_team2_years[0]} to {longest_streak_team2_years[1]})</p>"
 
        html_response += "<table><tr><th>Season</th><th>Week</th><th>Date</th><th>Winner</th><th>Venue</th><th>Home Team</th><th>Home Score</th><th>Away Team</th><th>Away Score</th><th>Win Diff.</th></tr>"
        for _, game in games_df.iterrows():
            # Format the date
            date = datetime.strptime(game['_date'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%b-%d")
            # Format the venue
            venue = game['venue'] if game['venue'] else "-"
            # Format the winner as "Team (Score-Score)"
            winner = f"{game['winner']} ({game['home_score']}-{game['away_score']})" if game['winner'] == game['home_team'] else f"{game['winner']} ({game['away_score']}-{game['home_score']})"
            # Calculate the win difference
            win_diff = abs(game['home_score'] - game['away_score'])
            # Bold the winning team
            home_team = f"<b>{game['home_team']}</b>" if game['home_team'] == game['winner'] else game['home_team']
            away_team = f"<b>{game['away_team']}</b>" if game['away_team'] == game['winner'] else game['away_team']
            if game['season'] > 2009:
                season = f"<a href='#' onclick=\"fillAndSend('Tell me more about the {game['home_team']} vs {game['away_team']} game in {game['season']}')\">{game['season']}</a>"
                home_team = f"<a href='#' onclick=\"fillAndSend('Show me the roster for {game['home_team']} in {game['season']}')\">{game['home_team']}</a>"
            else:
                season = game['season']
                home_team = game['home_team']
            html_response += f"<tr><td>{season}</td><td>{game['week']}</td><td>{date}</td><td>{winner}</td><td>{venue}</td><td>{home_team}</td><td>{game['home_score']}</td><td>{away_team}</td><td>{game['away_score']}</td><td>{win_diff}</td></tr>"
        html_response += "</table>"




        # Add a button to download the data as a CSV file
        html_response += '<button onclick="downloadCSV()">Download as CSV</button>'

        return {
            "llmfunctiondata": matchup_history,
            "html_response": html_response
        }
    except Exception as e:
        print(f"An error occurred when calling get_team_matchup_history: {e}")
        return None    
    
def get_roster_by_position(team, year, position):
    print(f"Getting roster for {team} in {year} for position {position}")
    try:
        roster = TeamsAPI.get_roster(team=team, year=year)
        # Filter the roster to only include players with the specified position
        roster = [player.to_dict() for player in roster if player.position == position]
        return roster
    except Exception as e:
        print(f"An error occurred when calling get_roster_by_position: {e}")
        return None



global_map_html = ""



def get_full_roster(team, year):
    print(f"Getting roster for {team} in {year}")
    try:
        roster = TeamsAPI.get_roster(team=team, year=year)
        # Convert each Player object to a dictionary
        full_roster = [player.to_dict() for player in roster]

        # Filter out the specified columns and sort the roster
        filtered_roster = [{k: v for k, v in player.items() if k not in ["home_latitude", "home_longitude", "home_county_fips", "recruit_ids"]} for player in full_roster]
        sorted_roster = sorted(filtered_roster, key=lambda x: (x['position'] if x['position'] is not None else '', x['year'] if x['year'] is not None else 0, x['jersey'] if x['jersey'] is not None else 0))

        # Create a DataFrame from the roster
        df = pd.DataFrame(sorted_roster)
        print(df)
        print(df['year'].isnull().sum())  # Print the number of null 'year' values
        print(df['position'].isnull().sum())  # Print the number of null 'position' values

        df['year'] = df['year'].fillna(0)  # Fill null 'year' values with 0
        df['position'] = df['position'].fillna('Unknown')  # Fill null 'position' values with 'Unknown'

        df['year'] = df['year'].astype(str)  # Convert 'year' to string

        print(df['year'].isnull().count())  # Print the number of null 'year' values
        print(df['position'].isnull().count())  # Print the number of null 'position' values
        print(df)   

        # Select only 'position' and 'year' columns
        df = df[['position', 'year', 'last_name']]
        print(df)

        # Create a summary table of the number of players by position and year
        summary_table = df.pivot_table(index='position', columns='year', aggfunc='count', fill_value=0, margins=True, margins_name='Total')
 
        # Convert the summary table to HTML
        summary_table_html = summary_table.to_html()

        # Create a map centered around the United States
        m = folium.Map(location=[37.8, -96], zoom_start=4)

        # Add a marker for each player
        for player in full_roster:
            if player['home_latitude'] is not None and player['home_longitude'] is not None:
                folium.Marker(
                    location=[player['home_latitude'], player['home_longitude']],
                    popup=f"{player['jersey']} {player['first_name']} {player['last_name']} - {player['position']} - {player['height'] // 12}'{player['height'] % 12}\" - {player['weight']} - {player['home_city']}, {player['home_state']}",
                    icon=folium.Icon(icon="shield"),
                ).add_to(m)

        # Convert the map to HTML and store it in the global variable
        global global_map_html
        global_map_html = m._repr_html_()

        # Prepare the HTML table
        html_table = "<table><tr><th>Position</th><th>Year</th><th>Jersey</th><th>First Name</th><th>Last Name</th><th>Height</th><th>Weight</th><th>Home City</th><th>Home State</th></tr>"
        for player in sorted_roster:
            html_table += f"<tr><td>{player['position']}</td><td>{player['year']}</td><td>{player['jersey']}</td><td>{player['first_name']}</td><td>{player['last_name']}</td><td>{player['height']}</td><td>{player['weight']}</td><td>{player['home_city']}</td><td>{player['home_state']}</td></tr>"
        html_table += "</table>"

        # Prepare the HTML response
        html_response = f"<h2>Roster for {team} in {year}</h2><p><a href='/map' target='_blank'>View Map by Player Hometown</a></p>" + "</p><h3>Summary by Position</h3><p>" + summary_table_html + "</p><h3>Full Roster</h3>" + html_table + "</p>"

        return {
            "llmfunctiondata": sorted_roster,
            "html_response": html_response
        }
    except Exception as e:
        print(f"An error occurred when calling get_full_roster: {e}")
        return None

def get_rankings(year, week=None, season_type=None):
    print(f"Getting rankings for {year} week {week} season type {season_type}")
    args = {k: v for k, v in {"year": year, "week": week, "season_type": season_type}.items() if v is not None}
    try:
        rankings = RankingsAPI.get_rankings(**args)
        rankings_list = [ranking.to_dict() for ranking in rankings]

        # If week is None, only return the latest week to the LLM
        if week is None:
            latest_week = max(ranking['week'] for ranking in rankings_list)
            llmfunctiondata = [ranking for ranking in rankings_list if ranking['week'] == latest_week]
        else:
            llmfunctiondata = rankings_list

        # Prepare the HTML response
        html_response = f"<h2>Rankings for {year}</h2>"
        # Sort the rankings_list by week in descending order
        rankings_list.sort(key=lambda x: x.get('week', 0), reverse=True)
        for ranking in rankings_list:
            html_response += f"<h3>{ranking.get('seasonType', 'N/A')} - Week {ranking.get('week', 'N/A')}</h3>"
            # Create a dictionary to store the rankings by poll
            rankings_by_poll = {}
            for poll in ranking['polls']:
                if poll['poll'] not in rankings_by_poll:
                    rankings_by_poll[poll['poll']] = ["N/A"] * 25
                for rank in poll['ranks']:
                    rankings_by_poll[poll['poll']][rank.get('rank', 0) - 1] = f"{rank.get('school', 'N/A')} ({rank.get('conference', 'N/A')}, {rank.get('points', 'N/A')})"

            # Prepare the HTML response for each week
            html_response += "<table><tr><th>Rank</th>" + "".join([f"<th>{poll}</th>" for poll in rankings_by_poll.keys()]) + "</tr>"
            for i in range(25):
                html_response += "<tr><td>" + str(i + 1) + "</td>" + "".join([f"<td>{rankings_by_poll[poll][i]}</td>" for poll in rankings_by_poll.keys()]) + "</tr>"
            html_response += "</table>"

        return {
            "llmfunctiondata": llmfunctiondata,
            "html_response": html_response
        }
    except Exception as e:
        print(f"An error occurred when calling get_rankings: {e}")
        return None



def get_team_records(year=None, team=None, conference=None):
    print(f"Getting team records for {year} {team} {conference}")
    # Only include parameters in the arguments if they are not None
    args = {k: v for k, v in {"year": year, "team": team, "conference": conference}.items() if v is not None}
    team_records = games.get_team_records(**args)
    return [record.to_dict() for record in team_records]  # Convert each TeamRecord object to a dictionary

def get_team_records_multiyear(start_year, end_year, team, conference=None):
    if end_year - start_year > 5:
        keys_to_remove = ['conferenceGames', 'homeGames', 'awayGames']
    else:
        keys_to_remove = []

    records = []
    for year in range(start_year, end_year + 1):
        print(f"Getting team records for {year} {team} {conference}")
        year_records = get_team_records(year=year, team=team, conference=conference)
        for record in year_records:
            for key in keys_to_remove:
                record.pop(key, None)
        records.extend(year_records)
    return records


def get_list_of_cfb_games(year, week=None, season_type=None, team=None, home=None, away=None, conference=None, division=None, id=None):
    # Only include parameters in the arguments if they are not None
    print(f"Getting games for {year} {week} {season_type} {team} {home} {away} {conference} {division} {id}")
    args = {k: v for k, v in {"year": year, "week": week, "team": team, "home": home, "away": away, "conference": conference, "division": division, "id": id}.items() if v is not None}
    
    # If no season_type is specified, call the games.get_games API for both season_type="regular" and season_type="postseason" and combine the results
    if season_type is None:
        args["season_type"] = "regular"
        regular_season_games = games.get_games(**args)
        args["season_type"] = "postseason"
        postseason_games = games.get_games(**args)
        gamelist = regular_season_games + postseason_games
    else:
        gamelist = games.get_games(**args)

    gamelist = [game.to_dict() for game in gamelist]  # Convert each Game object to a dictionary

    # Prepare the HTML response
    # Prepare the HTML response
    # Create a header with the year and non-blank parameters
    header = f"Results for "
    parameters = [f"{k.capitalize()}: {v}" for k, v in args.items() if v is not None]
    header += ", ".join(parameters)
    html_response = f"<h2>{header}</h2><ul>"
    
    html_response += "<table><tr><th>Game Date</th><th>Week</th><th>Matchup</th><th>Season Type</th><th>Conf Game</th><th>Venue</th><th>Highlights</th><th>More</th></tr>"

    for game in gamelist:
        # Format the date
        date = datetime.strptime(game['start_date'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%b-%d-%y")
        # Format the matchup
        matchup = f"{game['home_team']} {game['home_points']} vs {game['away_team']} {game['away_points']}"
        # Format the conference game
        conf_game = "Yes" if game['conference_game'] else "No"
        # Format the highlights
        print(game['highlights'])
        highlights = f"<a href='{game['highlights']}' target='_blank'>Watch Highlights</a>" if game['highlights'] else "-"
        # Format the more link
        more = f"<a href='#' onclick=\"fillAndSend('Tell me more about the {game['home_team']} vs {game['away_team']} game in {game['season']}')\">More</a>"

        html_response += f"<tr><td>{date}</td><td>{game['week']}</td><td>{matchup}</td><td>{game['season_type'].capitalize()}</td><td>{conf_game}</td><td>{game['venue']}</td><td>{highlights}</td><td>{more}</td></tr>"

    html_response += "</table>"

    
    return {
        "llmfunctiondata": gamelist,
        "html_response": html_response
    }

    
def get_team_game_stats(year, game_id, week=None, season_type=None, team=None, conference=None, classification=None):
    print(f"Getting team game stats for {year} {game_id} {week} {season_type} {team} {conference} {classification}")
    args = {k: v for k, v in {"year": year, "game_id": game_id, "week": week, "season_type": season_type, "team": team, "conference": conference, "classification": classification}.items() if v is not None}
    team_game_stats = games.get_team_game_stats(**args)
    return [stat.to_dict() for stat in team_game_stats]

def get_player_game_stats(year, week=None, season_type=None, team=None, conference=None, category=None, game_id=None):
    print(f"Getting player game stats for {year} {week} {season_type} {team} {conference} {category} {game_id}")
    args = {k: v for k, v in {"year": year, "week": week, "season_type": season_type, "team": team, "conference": conference, "category": category, "game_id": game_id}.items() if v is not None}
    player_game_stats = games.get_player_game_stats(**args)
    return [stat.to_dict() for stat in player_game_stats]



def get_game_stats_for_specific_matchup(year, team1, team2):
    print(f"Getting game stats for {year} {team1} {team2}")
    try:
        # Get the games for team1 in the regular season and post season
        regular_season_games = get_list_of_cfb_games(year=year, season_type="regular", team=team1)
        post_season_games = get_list_of_cfb_games(year=year, season_type="postseason", team=team1)

        # Check if regular_season_games and post_season_games are dictionaries
        if isinstance(regular_season_games, dict) and isinstance(post_season_games, dict):
            # Combine the regular season and post season games
            all_games = regular_season_games['llmfunctiondata'] + post_season_games['llmfunctiondata']
        else:
            # Handle the case where no games were found
            all_games = []
        # Find the game where team1 played against team2
        matchup_game = next((game for game in all_games if game['home_team'] == team2 or game['away_team'] == team2), None)

        if matchup_game is None:
            return {
                "llmfunctiondata": f"{team1} did not play against {team2} in the {year} season.",
                "html_response": f"<p>{team1} did not play against {team2} in the {year} season.</p>"
            }

        # Get the game stats for the matchup game
        game_stats = get_team_game_stats(year=year, game_id=matchup_game['id'])

        # Prepare the HTML response
        html_response = "<h2>Game Stats for the Matchup</h2>"
        html_response += "<table><tr><th>Stat</th><th>Value</th></tr>"
        for stat, value in game_stats.items():
            html_response += f"<tr><td>{stat}</td><td>{value}</td></tr>"
        html_response += "</table>"

        return {
            "llmfunctiondata": game_stats,
            "html_response": html_response
        }
    except Exception as e:
        print(f"An error occurred when calling get_game_stats_for_specific_matchup: {e}")
        return None

def get_game_info(year, team1, team2):
    print(f"Getting team vs team matchup info for {year} {team1} {team2}")
    try:
        print(f"Getting list of cfb games for {year} {team1} ")
        all_games = get_list_of_cfb_games(year=year, team=team1)

        # Find the game where team1 played against team2
        matchup_game = next((game for game in all_games['llmfunctiondata'] if game['home_team'] == team2 or game['away_team'] == team2), None)

        if matchup_game is None:
            return {
                "llmfunctiondata": f"{team1} did not play against {team2} in the {year} season.",
                "html_response": f"<p>{team1} did not play against {team2} in the {year} season.</p>"
            }

        # Check if the year is greater than or equal to 2001 as the API only has data for these years
        if year >= 2001:
            # Get the game stats for the matchup game
            try:
                game_stats = get_team_game_stats(year=year, game_id=matchup_game['id'])
            except Exception as e:
                print(f"An error occurred when calling get_team_game_stats: {e}")
                game_stats = None
            # Get the player game stats for the matchup game
            try:
                player_game_stats = get_player_game_stats(year=year, game_id=matchup_game['id'])
            except Exception as e:
                print(f"An error occurred when calling get_player_game_stats: {e}")
                player_game_stats = None

            # Check if player_game_stats is None
            if game_stats is None:
                print("pgame_stats is None")
            else:
                print(f"Type game_stats:")
            # Check if player_game_stats is None
            if player_game_stats is None:
                print("player_game_stats is None")
            else:
                print(f"Type of player_game_stats: ")
        else:
            game_stats = None
            player_game_stats = None

        # If no game_stats or player_game_stats found, return the matchup_game info
        if not game_stats and not player_game_stats:
            return {
                "llmfunctiondata": f"Match found but no game stats or player game stats available. Match info: {matchup_game}",
                "html_response": f"<p>Match found but no game stats or player game stats available. Match info: {matchup_game}</p>"
            }

        # Remove 'id' from each stat dictionary
        for stat in player_game_stats:
            stat.pop('id', None)
        # Filter out any stat = "0"
        player_game_stats = [stat for stat in player_game_stats if all(value != "0" for value in stat.values())]
        
        # Filter out 'id' from each player's stats
        for team in player_game_stats:
            print(f"Type of team: {type(team)}, Value: {team}")
            if 'categories' in team:
                for category in team['categories']:
                    if 'types' in category:
                        for type_category in category['types']:  # Changed here
                            if 'athletes' in type_category:  # And here
                                for athlete in type_category['athletes']:  # And here
                                    athlete.pop('id', None)

        # Prepare the HTML response
        date = datetime.strptime(matchup_game['start_date'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%B %d, %Y")
        html_response = f"<h2>{matchup_game['home_team']} {matchup_game['home_points']} vs {matchup_game['away_team']} {matchup_game['away_points']}</h2>"
        html_response += f"<h3>Date: {date} | Venue: {matchup_game['venue']}</h3>"


        html_response += "<h3>Game Stats</h3>"

        # Initialize team stats dictionaries
        team_stats = {}

        # Iterate over each game_stat in game_stats
        for game_stat in game_stats:

            # Iterate over each team in the 'teams' key
            for team in game_stat['teams']:
                # Add the team's school and points to the team stats
                team_stats[team['school']] = {stat['category']: stat['stat'] for stat in team['stats']}

        # Prepare the table header
        # Get the team names
        home_team, away_team = matchup_game['home_team'], matchup_game['away_team']
        html_response += f"<table><tr><th>Stat</th><th><a href='#' onclick=\"fillAndSend('Who did {home_team} play in {year}')\">{home_team}</a></th><th><a href='#' onclick=\"fillAndSend('Who did {away_team} play in {year}')\">{away_team}</a></th><th>Differential</th></tr>"

        # Iterate over each stat category
        for category in game_stats[0]['teams'][0]['stats']:
            # Get the stats for each team
            home_team_stat = team_stats[home_team].get(category['category'], 'N/A')
            away_team_stat = team_stats[away_team].get(category['category'], 'N/A')

            # Calculate the differential
            try:
                differential = float(home_team_stat) - float(away_team_stat)
            except ValueError:
                differential = 'N/A'

            # Add the stats to the HTML response
            html_response += f"<tr><td>{category['category']}</td><td>{home_team_stat}</td><td>{away_team_stat}</td><td>{differential}</td></tr>"

        html_response += "</table>"



        html_response += "<h3>Player Game Stats</h3>"

        # Initialize the new table
        html_response += "<table><tr><th>Category</th><th>Type</th><th>Team</th><th>Player</th><th>Stat</th></tr>"

        # Create a dictionary to hold the stats in the desired order
        stats_dict = {}

        # Iterate over each game in player_game_stats
        for game in player_game_stats:
            # Iterate over each team in the 'teams' key
            for team in game['teams']:
                # Iterate over each category in the 'categories' key
                for category in team['categories']:
                    # Iterate over each stat_type in the 'types' key
                    for stat_type in category['types']:
                        # Add each player's stat to the dictionary if it's not '0'
                        for player in stat_type['athletes']:
                            if player['stat'] != '0':
                                # Create a key for the category and type if it doesn't exist
                                if (category['name'], stat_type['name']) not in stats_dict:
                                    stats_dict[(category['name'], stat_type['name'])] = []
                                # Add the team, player, and stat to the dictionary
                                stats_dict[(category['name'], stat_type['name'])].append((team['school'], player['name'], player['stat']))

        # Iterate over the dictionary in the order of Category, Type, Team, Player
        for (category, stat_type), stats in sorted(stats_dict.items()):
            for team, player, stat in sorted(stats):
                html_response += f"<tr><td>{category}</td><td>{stat_type}</td><td>{team}</td><td>{player}</td><td>{stat}</td></tr>"

        html_response += "</table>"



        # Return the game stats, player game stats, and HTML response
        return {
            "llmfunctiondata": {
                "game_stats": game_stats,
                "player_game_stats": player_game_stats,
            },
            "html_response": html_response
        }

    except Exception as e:
        print(f"An error occurred when calling get_game_info: {e}")
        return None


def get_team_info(team=None, conference=None):
    print(f"Getting team info for team {team} and conference {conference}")
    try:
        args = {k: v for k, v in {"conference": conference}.items() if v is not None}
        team_info = TeamsAPI.get_teams(**args)
        team_info = [info.to_dict() for info in team_info]  # Convert Team objects to dictionaries
        if team is not None:
            team_info = [info for info in team_info if info['school'] == team]
        return team_info
    except Exception as e:
        print(f"An error occurred when calling get_team_info: {e}")
        return None

def play_next(team):
    print(f"Getting next game for {team}")
    try:
        # Get the current year and date
        current_year = datetime.now().year
        current_date = datetime.now().date()

        # Get the games for the current year for the specified team
        games = get_list_of_cfb_games(year=current_year, team=team)

        # Filter the games to find the next game that is after the current date
        next_game = next((game for game in games if datetime.strptime(game['start_date'], '%Y-%m-%dT%H:%M:%S.%fZ').date() > current_date), None)

        if next_game is None:
            return f"{team} has no more games this year."

        return next_game
    except Exception as e:
        print(f"An error occurred when calling play_next: {e}")
        return None

def play_next_conference(conference, division=None):
    print(f"Getting next game for conference {conference} and division {division}")
    try:
        teams = get_team_info(conference=conference)
        if division is not None:
            teams = [team for team in teams if team['division'] == division]
        next_games = {team['school']: play_next(team['school']) for team in teams}
        return next_games
    except Exception as e:
        print(f"An error occurred when calling play_next_conference: {e}")
        return None


# Define the function for the model
functions = [{
    "name": "get_list_of_cfb_games",
    "output": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "attendance": {"type": "integer"},
                "away_conference": {"type": "string"},
                "away_division": {"type": "string"},
                "away_id": {"type": "integer"},
                "away_line_scores": {"type": "array", "items": {"type": "integer"}},
                "away_points": {"type": "integer"},
                "away_post_win_prob": {"type": "number"},
                "away_postgame_elo": {"type": "integer"},
                "away_pregame_elo": {"type": "integer"},
                "away_team": {"type": "string"},
                "completed": {"type": "boolean"},
                "conference_game": {"type": "boolean"},
                "excitement_index": {"type": "number"},
                "highlights": {"type": "string"},
                "home_conference": {"type": "string"},
                "home_division": {"type": "string"},
                "home_id": {"type": "integer"},
                "home_line_scores": {"type": "array", "items": {"type": "integer"}},
                "home_points": {"type": "integer"},
                "home_post_win_prob": {"type": "number"},
                "home_postgame_elo": {"type": "integer"},
                "home_pregame_elo": {"type": "integer"},
                "home_team": {"type": "string"},
                "id": {"type": "integer"},
                "neutral_site": {"type": "boolean"},
                "notes": {"type": "string"},
                "season": {"type": "integer"},
                "season_type": {"type": "string"},
                "start_date": {"type": "string"},
                "start_time_tbd": {"type": "boolean"},
                "venue": {"type": "string"},
                "venue_id": {"type": "integer"},
                "week": {"type": "integer"}
            },
            
        }
    },
    "parameters": {
        "type": "object",
        "properties": {
            "year": {"type": "integer"},
            "week": {"type": "integer", "default": None},
            "season_type": {"type": "string", "default": "regular", "enum": ["regular", "postseason"]},
            "team": {"type": "string", "default": None},
            "home": {"type": "string", "default": None},
            "away": {"type": "string", "default": None},
            "conference": {"type": "string", "default": None, "enum": valid_conferences},
            "division": {"type": "string", "default": "fbs", "enum": ["fbs", "fcs","ii","iii"]},
            "id": {"type": "integer", "default": None}
        }
    }
},
    {
        "name": "get_team_records",
        "output": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer"},
                    "team": {"type": "string"},
                    "conference": {"type": "string"},
                    "division": {"type": "string"},
                    "expected_wins": {"type": "number"},
                    "total": {"type": "object"},
                    "conference_games": {"type": "object"},
                    "home_games": {"type": "object"},
                    "away_games": {"type": "object"},
                }
            }
        },
        "parameters": {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "default": None},
                "team": {"type": "string", "default": None},
                "conference": {"type": "string", "default": None},
            }
        },
        "parameters": {
            "type": "object",
            "properties": {
                "year": {"type": "integer"},
                "game_id": {"type": "integer"},
                "week": {"type": "integer", "default": None},
                "season_type": {"type": "string", "default": None},
                "team": {"type": "string", "default": None},
                "conference": {"type": "string", "default": None},
                "classification": {"type": "string", "default": None}
            }
        }
    },
]

#functions.append({
#    "name": "get_player_game_stats",
#    "output": {
#        "type": "array",
#        "items": {
#            "type": "object",
#            "properties": {
#                "id": {"type": "integer"},
#                "teams": {
#                    "type": "array",
#                    "items": {
#                        "type": "object",
#                        "properties": {
#                            "school": {"type": "string"},
#                            "conference": {"type": "string"},
#                            "home_away": {"type": "string"},
#                            "points": {"type": "integer"},
#                            "categories": {
#                                "type": "array",
#                                "items": {
#                                    "type": "object",
#                                    "properties": {
#                                        "name": {"type": "string"},
#                                        "types": {
#                                            "type": "array",
#                                            "items": {
#                                                "type": "object",
#                                                "properties": {
#                                                    "name": {"type": "string"},
#                                                    "athletes": {
#                                                        "type": "array",
#                                                        "items": {
#                                                            "type": "object",
#                                                            "properties": {
#                                                                "id": {"type": "integer"},
#                                                                "name": {"type": "string"},
#                                                                "stat": {"type": "string"}
#                                                            }
#                                                        }
#                                                    }
#                                                }
#                                            }
#                                        }
#                                    }
#                                }
#                            }
#                        }
#                    }
#                }
#            }
#        }
#    },
#    "parameters": {
#        "type": "object",
#        "properties": {
#            "year": {"type": "integer"},
#            "week": {"type": "integer", "default": None},
#            "season_type": {"type": "string", "default": None},
#            "team": {"type": "string", "default": None},
#            "conference": {"type": "string", "default": None},
#            "category": {"type": "string", "default": None},
#            "game_id": {"type": "integer", "default": None},
#        }
#    }
#})


functions.append({
    "name": "get_rankings",
    "output": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "season": {"type": "integer"},
                "season_type": {"type": "string"},
                "week": {"type": "integer"},
                "polls": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "poll": {"type": "string"},
                            "ranks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "rank": {"type": "integer"},
                                        "school": {"type": "string"},
                                        "conference": {"type": "string"},
                                        "first_place_votes": {"type": "integer"},
                                        "points": {"type": "integer"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    },
    "parameters": {
        "type": "object",
        "properties": {
            "year": {"type": "integer"},
            "week": {"type": "integer", "default": None},
            "season_type": {"type": "string", "default": None},
        }
    }
})

functions.append({
    "name": "get_full_roster",
    "output": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "team": {"type": "string"},
                "height": {"type": "integer"},
                "weight": {"type": "integer"},
                "jersey": {"type": "integer"},
                "year": {"type": "integer"},
                "position": {"type": "string"},
                "home_city": {"type": "string"},
                "home_state": {"type": "string"},
                "home_country": {"type": "string"},
                "home_latitude": {"type": "number"},
                "home_longitude": {"type": "number"},
                "home_county_fips": {"type": "string"},
                "recruit_ids": {"type": "array", "items": {"type": "integer"}}
            }
        }
    },
    "parameters": {
        "type": "object",
        "properties": {
            "team": {"type": "string"},
            "year": {"type": "integer"}
        }
    }
})

'''
functions.append({
    "name": "get_roster_by_position",
    "output": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "team": {"type": "string"},
                "height": {"type": "integer"},
                "weight": {"type": "integer"},
                "jersey": {"type": "integer"},
                "year": {"type": "integer"},
                "position": {"type": "string"},
                "home_city": {"type": "string"},
                "home_state": {"type": "string"},
                "home_country": {"type": "string"},
                "home_latitude": {"type": "number"},
                "home_longitude": {"type": "number"},
                "home_county_fips": {"type": "string"},
                "recruit_ids": {"type": "array", "items": {"type": "integer"}}
            }
        }
    },
    "parameters": {
        "type": "object",
        "properties": {
            "team": {"type": "string"},
            "year": {"type": "integer"},
            "position": {"type": "string", "enum": ['FB', 'S', 'LB', 'NT', 'DL', 'DE', 'DT', 'DB', 'LS', 'P', 'CB', 'G', 'OT', 'OL', 'TE', 'RB', 'WR', 'QB', 'PK']}
        }
    }
})
'''



'''
functions.append({
    "name": "get_game_stats_for_specific_matchup",
    "output": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "teams": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "school": {"type": "string"},
                            "conference": {"type": "string"},
                            "home_away": {"type": "string"},
                            "points": {"type": "integer"},
                            "stats": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "category": {"type": "string"},
                                        "stat": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    },
    "parameters": {
        "type": "object",
        "properties": {
            "year": {"type": "integer"},
            "team1": {"type": "string"},
            "team2": {"type": "string"}
        }
    }
})
'''



functions.append({
    "name": "get_game_info",
    "output": {
        "type": "object",
        "properties": {
            "game_stats": {
                "type": "array",
                "items": {
                    "type": "object"
                }
            },
            "player_game_stats": {
                "type": "array",
                "items": {
                    "type": "object"
                }
            }
        }
    },
    "parameters": {
        "type": "object",
        "properties": {
            "year": {"type": "integer"},
            "team1": {"type": "string"},
            "team2": {"type": "string"}
        }
    }
})

functions.append({
    "name": "get_team_matchup_history",
    "output": {
        "type": "object",
        "properties": {
            "team1": {"type": "string"},
            "team2": {"type": "string"},
            "startYear": {"type": "integer"},
            "endYear": {"type": "integer"},
            "team1Wins": {"type": "integer"},
            "team2Wins": {"type": "integer"},
            "ties": {"type": "integer"},
            "games": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "season": {"type": "integer"},
                        "week": {"type": "integer"},
                        "season_type": {"type": "string"},
                        "date": {"type": "string"},
                        "neutralSite": {"type": "boolean"},
                        "venue": {"type": "string"},
                        "homeTeam": {"type": "string"},
                        "homeScore": {"type": "integer"},
                        "awayTeam": {"type": "string"},
                        "awayScore": {"type": "integer"},
                        "winner": {"type": "string"}
                    }
                }
            }
        }
    },
    "parameters": {
        "type": "object",
        "properties": {
            "team1": {"type": "string"},
            "team2": {"type": "string"},
            "min_year": {"type": "integer", "default": None},
            "max_year": {"type": "integer", "default": None}
        }
    }
})

functions.append({
    "name": "get_team_records_multiyear",
    "output": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "year": {"type": "integer"},
                "team": {"type": "string"},
                "conference": {"type": "string"},
                "division": {"type": "string"},
                "expected_wins": {"type": "number"},
                "total": {"type": "object"},
                "conference_games": {"type": "object"},
                "home_games": {"type": "object"},
                "away_games": {"type": "object"},
            }
        }
    },
    "parameters": {
        "type": "object",
        "properties": {
            "start_year": {"type": "integer"},
            "end_year": {"type": "integer"},
            "team": {"type": "string"},
            "conference": {"type": "string", "default": None},
        }
    }
})

functions.append({
    "name": "play_next",
    "output": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "season": {"type": "integer"},
            "week": {"type": "integer"},
            "season_type": {"type": "string"},
            "start_date": {"type": "string"},
            "neutral_site": {"type": "boolean"},
            "conference_game": {"type": "boolean"},
            "attendance": {"type": "integer"},
            "venue_id": {"type": "integer"},
            "venue": {"type": "string"},
            "home_team": {"type": "string"},
            "home_conference": {"type": "string"},
            "home_points": {"type": "integer"},
            "home_line_scores": {"type": "array", "items": {"type": "integer"}},
            "away_team": {"type": "string"},
            "away_conference": {"type": "string"},
            "away_points": {"type": "integer"},
            "away_line_scores": {"type": "array", "items": {"type": "integer"}},
            "excitement_index": {"type": "number"}
        }
    },
    "parameters": {
        "type": "object",
        "properties": {
            "team": {"type": "string"},
        }
    }
})

functions.append({
    "name": "get_team_info",
    "output": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "school": {"type": "string"},
                "mascot": {"type": "string"},
                "abbreviation": {"type": "string"},
                "alt_name_1": {"type": "string"},
                "alt_name_2": {"type": "string"},
                "alt_name_3": {"type": "string"},
                "classification": {"type": "string"},
                "conference": {"type": "string"},
                "division": {"type": "string"},
                "color": {"type": "string"},
                "alt_color": {"type": "string"},
                "logos": {"type": "array", "items": {"type": "string"}},
                "twitter": {"type": "string"},
                "location": {
                    "type": "object",
                    "properties": {
                        "venue_id": {"type": "integer"},
                        "name": {"type": "string"},
                        "city": {"type": "string"},
                        "state": {"type": "string"},
                        "zip": {"type": "string"},
                        "country_code": {"type": "string"},
                        "timezone": {"type": "string"},
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"},
                        "elevation": {"type": "number"},
                        "capacity": {"type": "integer"},
                        "year_constructed": {"type": "integer"},
                        "grass": {"type": "boolean"},
                        "dome": {"type": "boolean"}
                    }
                }
            }
        }
    },
    "parameters": {
        "type": "object",
        "properties": {
            "team": {"type": "string", "default": None},
            "conference": {"type": "string", "default": None},
        }
    }
})

functions.append({
    "name": "play_next_conference",
    "output": {
        "type": "object",
        "additionalProperties": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "season": {"type": "integer"},
                "week": {"type": "integer"},
                "season_type": {"type": "string"},
                "start_date": {"type": "string"},
                "neutral_site": {"type": "boolean"},
                "conference_game": {"type": "boolean"},
                "attendance": {"type": "integer"},
                "venue_id": {"type": "integer"},
                "venue": {"type": "string"},
                "home_team": {"type": "string"},
                "home_conference": {"type": "string"},
                "home_points": {"type": "integer"},
                "home_line_scores": {"type": "array", "items": {"type": "integer"}},
                "away_team": {"type": "string"},
                "away_conference": {"type": "string"},
                "away_points": {"type": "integer"},
                "away_line_scores": {"type": "array", "items": {"type": "integer"}},
                "excitement_index": {"type": "number"}
            }
        }
    },
    "parameters": {
        "type": "object",
        "properties": {
            "conference": {"type": "string"},
            "division": {"type": "string", "default": None},
        }
    }
})

available_functions = {
    "get_list_of_cfb_games": get_list_of_cfb_games,
    "get_team_records": get_team_records,
    "get_rankings": get_rankings,
    "get_full_roster": get_full_roster,
    "get_game_info": get_game_info,
    "get_team_matchup_history": get_team_matchup_history,
    "get_team_records_multiyear": get_team_records_multiyear,
    "play_next": play_next,
    "get_team_info": get_team_info,
    "play_next_conference": play_next_conference,
}



def run_conversation(user_input):  # Add user_input as an argument
    from datetime import date
    today = date.today()
    messages = [
    {
        "role": "system",
        "content": f"You are a world-cass expert in college football. Provide helpful but concise answers to the following questions in MARKDOWN FORMAT. If showing a game result, include the score in your answer, as per this example: Week 4 (Sept 24): Alabama 55, Vanderbilt 3 (Id: {{id}}). Today's date is {today}.",
    }
    ]   

    user_message = {"role": "user", "content": user_input}

    # Append the user's message to the messages list
    messages.append(user_message)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=messages,
            functions=functions,
            function_call="auto",
        )
    except openai.error.InvalidRequestError as e:
        print(f"An error occurred: {e}")
        print("The token limit was exceeded. Please enter a new prompt.")
        myerrormessage = f"An error occurred: {e}"
        return myerrormessage
    

    response_message = response["choices"][0]["message"]

    if response_message.get("function_call"):
        function_name = response_message["function_call"]["name"]
        function_to_call = available_functions[function_name]
        function_args = json.loads(response_message["function_call"]["arguments"])
        try:
            function_response = function_to_call(**function_args)
        except TypeError as e:
            print(f"An error occurred: {e}")
            print("Please make sure you provide all required information.")
            return
        
         # Check if function_response is not None
        if function_response is not None:
            # Check if function_response contains a 'llmfunctiondata' key
            if 'llmfunctiondata' not in function_response:
                # If not, create a new function_response that includes the 'llmfunctiondata' key
                function_response = {
                    'llmfunctiondata': function_response,
                    'html_response': ''  # Default HTML response
                }

            messages.append(response_message)
            messages.append(
                {
                    "role": "function",
                    "name": function_name,
                    "content": json.dumps(function_response['llmfunctiondata']),
                }
            )
    # Append the assistant's message to the messages list
    if not response_message.get("function_call"):
        messages.append(response_message)

    try:
        second_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=messages,
        )
    except openai.error.InvalidRequestError as e:
        print(f"An error occurred: {e}")
        print("The token limit was exceeded. Please enter a new prompt.")
        errormessage = f"An error occurred: {e}"
        return errormessage
    
    # Get the response content
    response_content = second_response['choices'][0]['message']['content']

    # Replace line breaks with <br> for HTML
    response_content_html = response_content.replace('\n', '<br>')

    # Return the response as JSON. 
    return {
        "llm_response": response_content_html, # goes to the chatbox
        "html_response": function_response['html_response'] if function_response else '' # goes to the more info section
    }



#if __name__ == "__main__":
#    app.run(debug=True)

if __name__ == "__main__":
    if os.getenv("REPLIT_DB_URL"):
        app.run(host='0.0.0.0', port=8080)  # Running on Replit
    else:
        app.run(debug=True)  # Running locally


#while True:
#    print(run_conversation())
#    continue_chat = input('Do you want to continue the conversation? (yes/no): ')
#    if continue_chat.lower() != 'yes':
#        break
