from __future__ import print_function
import time
import cfbd
from cfbd.rest import ApiException
from pprint import pprint
import openai
import json


# Configure API key authorization: ApiKeyAuth
configuration = cfbd.Configuration()
configuration.api_key['Authorization'] = os.getenv('CFBD_API_KEY')
configuration.api_key_prefix['Authorization'] = 'Bearer'


# create an instance of the API class
games = cfbd.GamesApi(cfbd.ApiClient(configuration))
conferences_api = cfbd.ConferencesApi(cfbd.ApiClient(configuration))
RankingsAPI = cfbd.RankingsApi(cfbd.ApiClient(configuration))
TeamsAPI = cfbd.TeamsApi(cfbd.ApiClient(configuration))


def get_team_matchup_info(team1, team2, min_year=None, max_year=None):
    try:
        args = {k: v for k, v in {"min_year": min_year, "max_year": max_year}.items() if v is not None}
        matchup_info = TeamsAPI.get_team_matchup(team1, team2, **args)
        return matchup_info.to_dict()
    except Exception as e:
        print(f"An error occurred when calling get_team_matchup_info: {e}")
        return None

def get_roster_by_position(team, year, position):
    try:
        roster = TeamsAPI.get_roster(team=team, year=year)
        # Filter the roster to only include players with the specified position
        roster = [player.to_dict() for player in roster if player.position == position]
        return [player.to_dict() for player in roster]
    except Exception as e:
        print(f"An error occurred when calling get_roster_by_position: {e}")
        return None

def get_roster(team, year):
    try:
        roster = TeamsAPI.get_roster(team=team, year=year)
        return [player.to_dict() for player in roster]
    except Exception as e:
        print(f"An error occurred when calling get_roster: {e}")
        return None

def get_rankings(year, week=None, season_type=None):
    args = {k: v for k, v in {"year": year, "week": week, "season_type": season_type}.items() if v is not None}
    rankings = RankingsAPI.get_rankings(**args)
    return [ranking.to_dict() for ranking in rankings]




def get_team_records(year=None, team=None, conference=None):
    # Only include parameters in the arguments if they are not None
    args = {k: v for k, v in {"year": year, "team": team, "conference": conference}.items() if v is not None}
    team_records = games.get_team_records(**args)
    return [record.to_dict() for record in team_records]  # Convert each TeamRecord object to a dictionary


def get_cfb_games(year, week=None, season_type="regular", team=None, home=None, away=None, conference=None, division=None, id=None):
    # Only include parameters in the arguments if they are not None
    args = {k: v for k, v in {"year": year, "week": week, "season_type": season_type, "team": team, "home": home, "away": away, "conference": conference, "division": division, "id": id}.items() if v is not None}
    gamelist = games.get_games(**args)
    return [game.to_dict() for game in gamelist]  # Convert each Game object to a dictionary
    
def get_team_game_stats(year, game_id, week=None, season_type=None, team=None, conference=None, classification=None):
    # Only include parameters in the arguments if they are not None
    args = {k: v for k, v in {"year": year, "game_id": game_id, "week": week, "season_type": season_type, "team": team, "conference": conference, "classification": classification}.items() if v is not None}
    team_game_stats = games.get_team_game_stats(**args)
    return [stat.to_dict() for stat in team_game_stats]  # Convert each TeamGame object to a dictionary

def get_player_game_stats(year, week=None, season_type=None, team=None, conference=None, category=None, game_id=None):
    args = {k: v for k, v in {"year": year, "week": week, "season_type": season_type, "team": team, "conference": conference, "category": category, "game_id": game_id}.items() if v is not None}
    player_game_stats = games.get_player_game_stats(**args)
    return [stat.to_dict() for stat in player_game_stats]

def get_game_stats_for_specific_matchup(year, team1, team2):
    try:
        # Get the games for team1 in the regular season and post season
        regular_season_games = get_cfb_games(year=year, season_type="regular", team=team1)
        post_season_games = get_cfb_games(year=year, season_type="postseason", team=team1)

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

def get_team_vs_team_matchup_info(year, team1, team2):
    try:
        # Get the games for team1 in the regular season and post season
        regular_season_games = get_cfb_games(year=year, season_type="regular", team=team1)
        post_season_games = get_cfb_games(year=year, season_type="postseason", team=team1)

        # Combine the regular season and post season games
        all_games = regular_season_games + post_season_games

        # Find the game where team1 played against team2
        matchup_game = next((game for game in all_games if game['home_team'] == team2 or game['away_team'] == team2), None)

        if matchup_game is None:
            return f"{team1} did not play against {team2} in the {year} season."

        # Get the game stats for the matchup game
        game_stats = get_team_game_stats(year=year, game_id=matchup_game['id'])
        # Get the player game stats for the matchup game
        player_game_stats = get_player_game_stats(year=year, game_id=matchup_game['id'])

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


#team_records = get_team_records(year=2019, team="Alabama")
#print(team_records)

#gamestats = get_team_vs_team_matchup_info(year=2022, team1="Alabama", team2="Auburn")
#print(gamestats)
matchup_info = get_team_matchup_info("Alabama", "Auburn")
print(matchup_info)

#playerstats = get_player_game_stats(year=2022, game_id=401403854)   
#print(playerstats)

#rankings = get_rankings(year=2021, week=1)
#print(rankings)


