# College Football Chatbot

This is a chatbot built using Python and the OpenAI API that can answer questions about college football. 

## Features

The chatbot has access to the following data sources via API:

- [College Football Data API](https://collegefootballdata.com) - For getting game, team, and player stats
- [OpenAI API](https://openai.com/api/) - For powering the natural language chatbot capabilities 

It can provide information on:

- Games played each week 
- Team win/loss records
- Team rankings
- Rosters and player data
- Game stats and results for specific matchups

The chatbot can answer natural language questions about college football games, teams, players, rankings, etc.

## Usage

The chatbot is built as a Flask web application. To use it:

1. Clone the repository
2. Sign up for API keys from College Football Data and OpenAI
3. Set the API keys as environment variables
4. Run `python main.py` to start the Flask web server
5. Navigate to `http://localhost:5000` 
6. Type your question in the input field and click Submit

The chatbot will respond with the answer.

## Dependencies

- Python 3.7+
- Flask
- CollegeFootballData Python SDK 
- OpenAI Python SDK

## Configuration

The API keys need to be set as environment variables:

- `CFBD_API_KEY` - College Football Data API key 
- `OPENAI_API_KEY` - OpenAI API key

## Documentation

The main functions for retrieving data are:

- `get_list_of_cfb_games` - Get list of games for a given week/season
- `get_team_records` - Get win/loss records for a team  
- `get_team_game_stats` - Get box score stats for a game
- `get_player_game_stats` - Get player stats for a game
- `get_rankings` - Get AP top 25 or other poll rankings
- `get_roster_by_position` - Get team's roster filtered by position
- `get_full_roster` - Get full roster for a team/season 
- `get_game_info` - Get high-level stats and info for a matchup
- `get_team_matchup_history` - Get historical wins/losses between two teams

The `run_conversation` function handles taking the user's natural language input, calling the appropriate data function, and returning the chatbot response.

## License

This project is open source and available under the [MIT License](LICENSE).
