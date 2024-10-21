from openai import AzureOpenAI
from flask import Flask, request, jsonify, render_template
import logging
import hashlib
import os
import random


# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO)

client = AzureOpenAI(azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
api_version="2023-05-15",
api_key=os.getenv("AZURE_OPENAI_API_KEY"))

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')

# Initialize OpenAI with Azure credentials
@app.route('/generate_idea', methods=['POST'])
def generate_idea():    
    try:
        # Extract data from the POST request
        data = request.json
        themes = data.get('themes', [])
        mechanisms = data.get('mechanisms', [])
        player_count_min = data.get('player_count_min', 2)
        player_count_max = data.get('player_count_max', 4)
        game_length = data.get('game_length', '1 hour')
        game_type = data.get('game_type', 'competitive')
        theme_num = data.get('theme_num', 2)
        mechanism_num = data.get('mechanism_num', 2)

        # Create the prompt
        prompt = create_prompt(themes, mechanisms, player_count_min=player_count_min, player_count_max=player_count_max, game_length=game_length, game_type=game_type, theme_num=theme_num, mechanism_num=mechanism_num)

        # Generate the board game idea
        # game_idea = prompt_to_response(prompt)
        # game_idea = generate_idea_with_cache(prompt)
        try:
            game_idea = generate_idea_with_cache(prompt)
        except openai.error.OpenAIError as e:
            return jsonify({'error': 'Failed to generate idea from OpenAI: ' + str(e)}), 500
        logging.info(f"Generated idea: {game_idea}")
        # Return the generated idea in JSON format
        return jsonify({'board_game_idea': game_idea}), 500

    except Exception as e:
        # Return an error response in case of an exception
        logging.error(f"Error occurred: {str(e)}")
        return jsonify({'error': str(e)}), 500



def prompt_to_response(prompt, deployment_name="gpt-4"):
    """
    This function generates a board game idea using the deployed model in Azure OpenAI.
    :param prompt: The input prompt to guide the model
    :param deployment_name: The name of the deployment in Azure OpenAI
    :return: The generated board game idea
    """
    response = client.chat.completions.create(model=deployment_name,  # Use the specified OpenAI model (you can use pre-trained models)
    messages=[{"role": "system", "content": "You are a board game designer generating ideas of board game."},
              {"role": "user", "content": prompt}],
    max_tokens=500,  # Adjust based on how long you want the completion to be
    temperature=0.7,  # Controls creativity (higher = more creative)
    top_p=0.9,  # Controls diversity via nucleus sampling
    frequency_penalty=0.5,  # Discourages repetition
    presence_penalty=0.0)
    return response.choices[0].message.content.strip()


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
        mechanisms_in_in = mechanisms + random.sample(mechanism_list, num_to_select)
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
