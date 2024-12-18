from openai import AzureOpenAI
from flask import Flask, request, jsonify, render_template
from flask_caching import Cache
import logging
import hashlib
import os
import datetime
import json
import threading

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO)

# Initialize OpenAI with Azure credentials
client = AzureOpenAI(azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
api_version="2023-05-15",
api_key=os.getenv("AZURE_OPENAI_API_KEY"))

# Intialize the flask app
app = Flask(__name__)
app.config.from_mapping({
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300
})

# Initialize cache
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})

# Global variables to track token usage
tokens_used_today = 0
tokens_lock = threading.Lock()
last_reset = datetime.date.today()

# Define your daily token limit
DAILY_TOKEN_LIMIT = (500*2)*20  # Set a limit

def reset_tokens_if_new_day():
    """
    Resets the daily token limit.
    """
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
    # Commented, ['usage'] is not available in Azure OpenAI
    # tokens_used = response['usage']['total_tokens']
    tokens_used = 500
    with tokens_lock:
        tokens_used_today += tokens_used
    return tokens_used

@app.route('/')
def index():
    """
    Render the main page of the app, the list of mechanisms and themes are imported from files.
    """
    # Load theme and mechanism lists from the files
    # May reorganize the file system when proect grows
    with open('theme_list.txt', 'r') as file:
        themes = sorted([line.strip() for line in file.readlines()])    
    with open('mechanism_list.txt', 'r') as file:
        mechanisms = sorted([line.strip() for line in file.readlines()])

    # Render the index.html template and pass the theme and mechanism lists to it
    return render_template('index.html', themes=themes, mechanisms=mechanisms)


@app.route('/generate_idea', methods=['POST'])
def generate_idea():    
    """
    Responds to the generate idea button in the html
    Routine to passes inputs to create_prompt then passes the prompt to cache_response
    return the repsonse and error code
    """
    try:
        # Get the input from the form
        data = request.get_json()
        app.logger.info(f"Received data: {data}")
        
        # Get selected themes from the form
        selected_themes = data.get('themes')
        # Get selected mechanisms from the form
        selected_mechanisms = data.get('mechanisms')
        # Remove duplicates 
        user_settings ={}
        user_settings["themes"] = list(set(selected_themes))
        user_settings["mechanisms"] = list(set(selected_mechanisms))

        # Error catcher
        if user_settings["themes"] is None or user_settings["mechanisms"] is None:
            app.logger.error("Themes or mechanisms not received properly!")
            return jsonify({"error": "Themes or mechanisms not received properly"}), 400

        # For prompt generation, text is easier to manage
        user_settings["themes_text"] = ' and '.join(user_settings["themes"])
        user_settings["mechanisms_text"] = ' and '.join(user_settings["mechanisms"])

        # Retrieve theme_num and mechanism_num, also other numerics from the form    
        user_settings["player_count_min"] = int(data.get('player_count_min', 2))
        user_settings["player_count_max"] = int(data.get('player_count_max', 4))
        user_settings["game_length"] = data.get('game_length', '1 hour')
        user_settings["game_type"] = data.get('game_type', 'Competitive')
        user_settings["theme_num"] = int(data.get('theme_num', 2))
        user_settings["mechanism_num"] = int(data.get('mechanism_num', 2))
        
        # A safeguard to avoid non-rational numerics
        if user_settings["player_count_max"] < user_settings["player_count_min"]:
            user_settings["player_count_max"] = user_settings["player_count_min"]        
        if user_settings["theme_num"] != len(user_settings["themes"]):
            user_settings["theme_num"] = len(user_settings["themes"])
        if user_settings["mechanism_num"] != len(user_settings["mechanisms"]):
            user_settings["mechanism_num"] = len(user_settings["mechanisms"])

        # Create prompt
        # prompts is directly the format of messages arguement of client.chat.completions.create()
        prompts = create_prompt_idea(user_settings)
        # Pass the prompts to the LLM
        game_idea, ecode = cache_response(prompts)
        # Return the response and error code
        if ecode==200:
            return jsonify({'board_game_idea': game_idea}), 200
        else:
            return jsonify({'error': game_idea}), ecode

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/generate_rules', methods=['POST'])
def generate_rules():    
    """
    Responds to the generate rules button in the html
    Routine to passes inputs to create_prompt then passes the prompt to cache_response
    return the repsonse and error code
    """
    try:
        # Get the input from the form
        data = request.get_json()

        # Prepare the other inputs propt generation
        user_settings ={}
        selected_mechanisms = data.get('mechanisms')
        user_settings["mechanisms"] = list(set(selected_mechanisms))
        user_settings["mechanisms_text"] = ' and '.join(user_settings["mechanisms"])
        user_settings["response_idea"] = data.get('response_idea')

        # Create prompt
        # prompts is directly the format of messages arguement of client.chat.completions.create()
        prompts = create_prompt_rules(user_settings)
        # Pass the prompts to the LLM
        game_rules, ecode = cache_response(prompts)

        # Return the response and error code
        if ecode==200:
            return jsonify({'board_game_rules': game_rules}), 200
        else:
            return jsonify({'error': game_rules}), ecode

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def create_prompt_idea(user_settings):
    """
    This function constructs the prompt for generating board game idea
    It takes a template, edit that for prompt engineering
    """
    with open('prompt_templates.json', 'r') as f:
        prompts_template = json.load(f)
    # System prompt
    system_prompt = prompts_template["system_prompt"]
    # User prompt, then input the settings passed in
    user_prompt_list = prompts_template["idea_user"]
    user_prompt_list[1] = user_prompt_list[1].replace("__themes__", user_settings["themes_text"])
    user_prompt_list[2] = user_prompt_list[2].replace("__mechanisms__", user_settings["mechanisms_text"])
    # Polish the prompt if the number of player is not a range
    if user_settings["player_count_max"]!=user_settings["player_count_min"]:
        user_prompt_list[3] = user_prompt_list[3].replace("__player_count_min__", str(user_settings["player_count_min"])).replace("__player_count_max__", str(user_settings["player_count_max"]))
    else:
        user_prompt_list[3] = user_prompt_list[3].replace("__player_count_min__ to __player_count_max__ players", f"{user_settings['player_count_min']} player")
    user_prompt_list[4] = user_prompt_list[4].replace("__game_length__", user_settings["game_length"])
    user_prompt_list[5] = user_prompt_list[5].replace("__game_type__", user_settings["game_type"])
    user_prompt = ''.join(user_prompt_list)

    # Assemble and return the prompt
    prompts = [{"role": "system", "content": system_prompt}]
    prompts += [{"role": "user", "content": user_prompt}]
    return prompts

def create_prompt_rules(user_settings):
    """
    This function constructs the prompt for generating board game rules.
    It takes a template, edit that for prompt engineering
    """
    with open('prompt_templates.json', 'r') as f:
        prompts_template = json.load(f)
    # System prompt
    system_prompt = prompts_template["system_prompt"]
    # User prompt, then input the settings passed in
    user_prompt_list = prompts_template["rules_user"]
    user_prompt_list[3] = user_prompt_list[3].replace("__mechanisms__", user_settings["mechanisms_text"])
    user_prompt = ''.join(user_prompt_list)
    # Assistant prompt, not from the template, but directly from the generated idea
    assistant_prompt = user_settings["response_idea"]

    # Assemble and return the prompt
    prompts = [{"role": "system", "content": system_prompt}]
    prompts += [{"role": "assistant", "content": assistant_prompt}]
    prompts += [{"role": "user", "content": user_prompt}]
    return prompts


def cache_response(prompts):
    """
    Passes the prompts into the client.chat.completions.create()
    But before that,
    see if the prompts are cached already, just not to waste tokens on redundant inputs
    """
    # Convert the prompts into string to hash
    prompt_combined = ''.join([f"{item['role']}: {item['content']}" for item in prompts])
    prompt_hash = hashlib.md5(prompt_combined.encode()).hexdigest()
    # Check if the response is already cached
    cached_response = cache.get(prompt_hash)
    if cached_response:
        return cached_response, 200
    # If not cached, generate a new response
    response_text, ecode = prompt_to_response(prompts)
    if ecode == 200:
        cache.set(prompt_hash, response_text)    
    return response_text, ecode

def prompt_to_response(prompts, deployment_name="gpt-4"):
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
    
    # A line for debugging locally, just not to send prompt everytime
    # return '\n'.join([f"{item['role']}: {item['content']}" for item in prompts]), 200

    # Use the specified OpenAI model (you can use pre-trained models)
    response = client.chat.completions.create(model=deployment_name, 
    messages=prompts,
    max_tokens=1000,
    temperature=0.7,
    top_p=0.9,
    frequency_penalty=0.5,
    presence_penalty=0.0)

    # Update token usage
    count_tokens_used(response)

    return response.choices[0].message.content.strip(), 200

if __name__ == '__main__':
    app.run(debug=True)
