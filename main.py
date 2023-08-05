from __future__ import print_function
import time
import cfbd
from cfbd.rest import ApiException
from pprint import pprint
import openai
import json
import os

from flask import Flask, request, render_template
app = Flask(__name__)

from flask import Markup

# setup the flast routing for the home page
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/get')
def get_bot_response():
    user_input = request.args.get('msg')  # Get data from input field
    response = run_conversation(user_input)  # Pass user_input to run_conversation
    return str(response)



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


def get_team_matchup_history(team1, team2, min_year=None, max_year=None):
    print(f"Getting matchup history for {team1} vs {team2} and years {min_year} to {max_year}")
    try:
        args = {k: v for k, v in {"min_year": min_year, "max_year": max_year}.items() if v is not None}
        matchup_info = TeamsAPI.get_team_matchup(team1, team2, **args)
        return matchup_info.to_dict()
    except Exception as e:
        print(f"An error occurred when calling get_team_matchup_info: {e}")
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

def get_full_roster(team, year):
    print(f"Getting roster for {team} in {year}")
    try:
        roster = TeamsAPI.get_roster(team=team, year=year)
        # Filter out the specified columns from the TeamsAPI json response
        filtered_roster = [{k: v for k, v in player.to_dict().items() if k not in ["home_latitude", "home_longitude", "home_county_fips", "recruit_ids"]} for player in roster]
        return filtered_roster
    except Exception as e:
        print(f"An error occurred when calling get_roster: {e}")
        return None


def get_rankings(year, week=None, season_type=None):
    print(f"Getting rankings for {year} week {week} season type {season_type}")
    args = {k: v for k, v in {"year": year, "week": week, "season_type": season_type}.items() if v is not None}
    try:
        rankings = RankingsAPI.get_rankings(**args)
        return [ranking.to_dict() for ranking in rankings]
    except Exception as e:
        print(f"An error occurred when calling get_rankings: {e}")
        return None


def get_team_records(year=None, team=None, conference=None):
    print(f"Getting team records for {year} {team} {conference}")
    # Only include parameters in the arguments if they are not None
    args = {k: v for k, v in {"year": year, "team": team, "conference": conference}.items() if v is not None}
    team_records = games.get_team_records(**args)
    return [record.to_dict() for record in team_records]  # Convert each TeamRecord object to a dictionary

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
    
    return [game.to_dict() for game in gamelist]  # Convert each Game object to a dictionary

    
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

        # Combine the regular season and post season games
        all_games = regular_season_games + post_season_games

        # Find the game where team1 played against team2
        matchup_game = next((game for game in all_games if game['home_team'] == team2 or game['away_team'] == team2), None)

        if matchup_game is None:
            return f"{team1} did not play against {team2} in the {year} season."

        # Get the game stats for the matchup game
        game_stats = get_team_game_stats(year=year, game_id=matchup_game['id'])

        return game_stats
    except Exception as e:
        print(f"An error occurred when calling get_game_stats_for_specific_matchup: {e}")
        return None


def get_game_info(year, team1, team2):
    print(f"Getting team vs team matchup info for {year} {team1} {team2}")
    try:
        # Get the games for team1 in the regular season and post season
        #regular_season_games = get_list_of_cfb_games(year=year, season_type="regular", team=team1)
        #post_season_games = get_list_of_cfb_games(year=year, season_type="postseason", team=team1)

        # Combine the regular season and post season games
        #all_games = regular_season_games + post_season_games
        all_games = get_list_of_cfb_games(year=year, team=team1)

        # Find the game where team1 played against team2
        matchup_game = next((game for game in all_games if game['home_team'] == team2 or game['away_team'] == team2), None)

        if matchup_game is None:
            return f"{team1} did not play against {team2} in the {year} season."

        # Check if the year is greater than or equal to 2001 as the API only has data for these years
        if year >= 2001:
            # Get the game stats for the matchup game
            game_stats = get_team_game_stats(year=year, game_id=matchup_game['id'])
            # Get the player game stats for the matchup game
            player_game_stats = get_player_game_stats(year=year, game_id=matchup_game['id'])
        else:
            game_stats = None
            player_game_stats = None

        # If no game_stats or player_game_stats found, return the matchup_game info
        if not game_stats and not player_game_stats:
            return f"Match found but no game stats or player game stats available. Match info: {matchup_game}"

        # Remove 'id' from each stat dictionary
        for stat in player_game_stats:
            stat.pop('id', None)
        # Filter out any stat = "0"
        player_game_stats = [stat for stat in player_game_stats if all(value != "0" for value in stat.values())]
        
        # Filter out 'id' from each player's stats
        for team in player_game_stats:
            if 'categories' in team:
                for category in team['categories']:
                    if 'types' in category:
                        for type in category['types']:
                            if 'athletes' in type:
                                for athlete in type['athletes']:
                                    athlete.pop('id', None)

        return json.dumps({
            "game_stats": game_stats,
            "player_game_stats": player_game_stats,
        })

    except Exception as e:
        print(f"An error occurred when calling get_specific_team_matchup_info: {e}")
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
        }
    },
     {
        "name": "get_team_game_stats",
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

functions.append({
    "name": "get_player_game_stats",
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
                            "categories": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "types": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "name": {"type": "string"},
                                                    "athletes": {
                                                        "type": "array",
                                                        "items": {
                                                            "type": "object",
                                                            "properties": {
                                                                "id": {"type": "integer"},
                                                                "name": {"type": "string"},
                                                                "stat": {"type": "string"}
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
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
            "team": {"type": "string", "default": None},
            "conference": {"type": "string", "default": None},
            "category": {"type": "string", "default": None},
            "game_id": {"type": "integer", "default": None},
        }
    }
})

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

available_functions = {
    "get_list_of_cfb_games": get_list_of_cfb_games,
    "get_team_records": get_team_records,
    "get_team_game_stats": get_team_game_stats,
    "get_player_game_stats": get_player_game_stats,
    "get_rankings": get_rankings,
    "get_roster_by_position": get_roster_by_position,
    "get_full_roster": get_full_roster,
    "get_game_info": get_game_info,
    "get_team_matchup_history": get_team_matchup_history
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

        messages.append(response_message)
        messages.append(
            {
                "role": "function",
                "name": function_name,
                "content": json.dumps(function_response),
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

    return response_content_html



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
