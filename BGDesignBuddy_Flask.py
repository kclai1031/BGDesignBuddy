from openai import AzureOpenAI
from flask import Flask, request, jsonify
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
@app.route('/hello')
def hello():
    return "Hello, World!"
if __name__ == '__main__':
    app.run()



