from openai import AzureOpenAI
from flask import Flask, request, jsonify, render_template
import logging
import hashlib
import os
import random
import datetime


def reset_tokens_if_new_day():
    global tokens_used_today, last_reset
    today = datetime.date.today()
    if today != last_reset:
        tokens_used_today = 0  # Reset token count
        last_reset = today
    return None

def count_tokens_used(response):
    """
    Extracts token usage from the response and updates the token counter.
    """
    global tokens_used_today
    # tokens_used = response['usage']['total_tokens']
    tokens_used = 500
    tokens_used_today += tokens_used
    return tokens_used

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO)

client = AzureOpenAI(azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
api_version="2023-05-15",
api_key=os.getenv("AZURE_OPENAI_API_KEY"))

app = Flask(__name__)

# Global variables to track token usage
tokens_used_today = 0
last_reset = datetime.date.today()

# Define your daily token limit
DAILY_TOKEN_LIMIT = (500*3)*20  # Set a limit

@app.route('/')
def index():
    # Load theme and mechanism lists from the files
    with open('theme_list.txt', 'r') as file:
        themes = sorted([line.strip() for line in file.readlines()])
    
    with open('mechanism_list.txt', 'r') as file:
        mechanisms = sorted([line.strip() for line in file.readlines()])

    # Render the index.html template and pass the theme and mechanism lists to it
    return render_template('index.html', themes=themes, mechanisms=mechanisms)


# Initialize OpenAI with Azure credentials
@app.route('/generate_idea', methods=['POST'])
def generate_idea():    
    try:
        data = request.get_json()
        app.logger.info(f"Received data: {data}")
        
        # Get selected themes from the form (both random and user-selected)
        selected_themes = data.get('themes')
        # Handle mechanism selection, allow up to 3 mechanisms
        selected_mechanisms = data.get('mechanisms')

        # Handle "Random" option by selecting random themes from the list
        with open('theme_list.txt', 'r') as file:
            all_themes = [line.strip() for line in file.readlines()]

        themes = []
        for theme in selected_themes:
            if theme == 'random':
                random_theme = random.choice(all_themes)
                themes.append(random_theme)
            else:
                themes.append(theme)

        # Load mechanism list from file
        with open('mechanism_list.txt', 'r') as file:
            all_mechanisms = [line.strip() for line in file.readlines()]

        mechanisms = []
        for mechanism in selected_mechanisms:
            if mechanism == 'random':
                random_mechanism = random.choice(all_mechanisms)
                mechanisms.append(random_mechanism)
            else:
                mechanisms.append(mechanism)

        if themes is None or mechanisms is None:
            app.logger.error("Themes or mechanisms not received properly!")
            return jsonify({"error": "Themes or mechanisms not received properly"}), 400


        # Retrieve theme_num and mechanism_num from the form        
        player_count_min = int(data.get('player_count_min', 2))
        player_count_max = int(data.get('player_count_max', 4))
        game_length = data.get('game_length', '1 hour')
        game_type = data.get('game_type', 'competitive')
        theme_num = int(data.get('theme_num', 2))
        mechanism_num = int(data.get('mechanism_num', 2))

        # Create prompt with the additional theme_num and mechanism_num
        prompt = create_prompt(themes, mechanisms, player_count_min=player_count_min, player_count_max=player_count_max,\
                                game_length=game_length, game_type=game_type,theme_num=theme_num, mechanism_num=mechanism_num)
        
        game_idea, ecode = generate_idea_with_cache(prompt)
        if ecode==200:
            return jsonify({'board_game_idea': game_idea}), 200
        else:
            return jsonify({'error': game_idea}), ecode

    except Exception as e:
        return jsonify({'error': str(e)}), 500




def prompt_to_response(prompt, deployment_name="gpt-4"):
    """
    This function generates a board game idea using the deployed model in Azure OpenAI.
    :param prompt: The input prompt to guide the model
    :param deployment_name: The name of the deployment in Azure OpenAI
    :return: The generated board game idea
    """
    global tokens_used_today
    reset_tokens_if_new_day()
    # Reject request if token limit exceeded
    if tokens_used_today >= DAILY_TOKEN_LIMIT:
        return 'Daily token limit exceeded. Try again tomorrow.', 429
    # return 'dummy', 200
    response = client.chat.completions.create(model=deployment_name,  # Use the specified OpenAI model (you can use pre-trained models)
    messages=[{"role": "system", "content": "You are a board game designer generating ideas of board game."},
              {"role": "user", "content": prompt}],
    max_tokens=500,  # Adjust based on how long you want the completion to be
    temperature=0.7,  # Controls creativity (higher = more creative)
    top_p=0.9,  # Controls diversity via nucleus sampling
    frequency_penalty=0.5,  # Discourages repetition
    presence_penalty=0.0)

    # Update token usage
    count_tokens_used(response)
    return response.choices[0].message.content.strip(), 200


def create_prompt(themes, mechanisms, player_count_min=2, player_count_max=4, game_length='1 hour', game_type='competitive', theme_num=2, mechanism_num=2):
    """
    This function constructs the prompt for generating board game ideas.
    :param themes: List of themes for the board game
    :param mechanisms: List of game mechanisms
    :param player_count_min: Minimum number of players
    :param player_count_max: Maximum number of players
    :param game_length: Estimated game length
    :param game_type: Type of game (competitive, cooperative, team-based)
    :theme_num: Number of themes
    :mechanism_num: Number of mechanisms
    :return: The constructed prompt
    """
    if len(themes)<theme_num:
        with open('theme_list.txt','r') as f:
            theme_list= f.readlines()
        num_to_select= theme_num-len(themes)
        themes_in = themes + random.sample(theme_list, num_to_select)
    else:
        themes_in=themes

    if len(mechanisms)<mechanism_num:
        with open('mechanism_list.txt','r') as f:
            mechanism_list= f.readlines()        
        num_to_select= mechanism_num-len(mechanisms)
        mechanisms_in = mechanisms + random.sample(mechanism_list, num_to_select)
    else:
        mechanisms_in=mechanisms

    theme_text = ' and '.join(themes_in)
    mechanism_text = ' and '.join(mechanisms_in)
    if player_count_max <= player_count_min:
        prompt = (f"Generate a {game_type} board game for {player_count_min} players with a {theme_text} theme, "
              f"using {mechanism_text} mechanisms. The game should last about {game_length}.")
    else:   
        prompt = (f"Generate a {game_type} board game for {player_count_min} to {player_count_max} players with a {theme_text} theme, "
              f"using {mechanism_text} mechanisms. The game should last about {game_length}.")
    return prompt

cache = {}

def generate_idea_with_cache(prompt):
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()

    # Check if the response is already cached
    if prompt_hash in cache:
        return cache[prompt_hash]
    
    # If not cached, generate a new idea
    game_idea = prompt_to_response(prompt)
    
    # Store the result in cache
    cache[prompt_hash] = game_idea
    
    return game_idea


def main():
    # Example inputs
    themes = ['Cthulhu Mythos', 'Horror', 'Adventure']  # Example from themes list
    mechanisms = ['Drafting', 'Hand Management']  # Example from mechanisms list
    player_count_min = 2  # Number of players
    player_count_max = 5  # Number of players
    game_length = '1 hour'  # Game duration
    game_type = 'copetitive'  # Type of game (competitive, cooperative, or team-based)

    # Create the prompt
    prompt = create_prompt(themes, mechanisms, player_count_min, player_count_max, game_length, game_type)
    print("Generated Prompt:", prompt)

    # Generate the board game idea
    # game_idea = prompt_to_response(prompt)
    try:
        game_idea = generate_idea_with_cache(prompt)
    except openai.error.OpenAIError as e:
        return jsonify({'error': 'Failed to generate idea from OpenAI: ' + str(e)}), 500

    print("Board Game Idea:", game_idea)


# if __name__ == "__main__":
#     main()


if __name__ == '__main__':
    app.run(debug=True)
