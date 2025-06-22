import os
import re
import requests
from openai import OpenAI

client = OpenAI(
	api_key=os.environ.get('GEMINI_API_KEY'),
	base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)


def encode_update(ror_id, description_of_change):
	script_dir = os.path.dirname(os.path.abspath(__file__))
	prompt_file_path = os.path.join(script_dir, "encode_prompt.txt")
	ror_api_url = 'https://api.ror.org/v2/organizations/' + ror_id
	r = requests.get(ror_api_url)
	if r.status_code == requests.codes.ok:
		with open(prompt_file_path, 'r', encoding="utf-8") as file:
			encode_prompt = file.read()
		record = str(r.json())
		try:
			encode_request = encode_prompt + record + description_of_change
			encode_response = client.chat.completions.create(model="gemini-2.5-pro",
			messages=[{"role": "user", "content": encode_request}])
			update = encode_response.choices[0].message.content
			return update
		except Exception:
			return None
