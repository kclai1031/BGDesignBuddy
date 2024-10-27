# Board Game Design Buddy

This repository contains the codebase for a **Board Game Design Buddy** that helps users brain storm board game concepts, rules. The app is currently hosted on Azure using OpenAI's GPT-4 for the content generation.

### Live Demo
You can access the live app hosted on Azure services here:
[Board Game Design Buddy](https://bgdesignbuddyapp.azurewebsites.net/)

### Features
- Generate board game descriptions.
- Step-by-step prompts for game idea and rules.
- Utilizes GPT-4 on Azure OpenAI for content generation.

### How It Works
The app generates board game ideas based on user-selected mechanisms and themes. It consists of three stages:
1. Generating a brief description.
2. Creating detailed rules.

### Technology Stack
- **Backend**: Flask (Python)
- **Frontend**: HTML/CSS, JavaScript
- **AI Integration**: GPT-4 via Azure OpenAI API
- **Hosting**: Azure App Services

### Installation
While the app is live, if you'd like to replicate it:
1. Clone the repository:
   ```bash
   git clone https://github.com/kclai1031/BGDesignBuddy.git
   cd BGDesignBuddy
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Please look for the comment in ```app.py```,
   ```python
   # Initialize OpenAI with Azure credentials
   ```
   , then set up your OpenAI API key on Azure Portal, if you are having a client on AzureOpenAI. For other clients, please edit the code accordingly.

5. Run the application:
   ```bash
   flask run
   ```

### Contributing

Feel free to submit pull requests or raise issues if you'd like to contribute or improve this project.

<p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/kclai1031/BGDesignBuddy">Board Game Design Buddy</a> by <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://www.linkedin.com/in/kingchunlai/">K. C. Lai</a> is licensed under <a href="https://creativecommons.org/licenses/by-nc/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">CC BY-NC 4.0<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1" alt=""><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1" alt=""><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/nc.svg?ref=chooser-v1" alt=""></a></p> </center>
</footer>
