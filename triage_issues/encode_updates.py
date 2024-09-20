import os
import re
import requests
from openai import OpenAI

client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))


def encode_update(ror_id, description_of_change):
	ror_api_url = 'https://api.ror.org/v2/organizations/' + ror_id
	r = requests.get(ror_api_url)
	if r.status_code == requests.codes.ok:
		with open('encode_prompt.txt', 'r') as file:
			encode_prompt = file.read()
		record = str(r.json())
		try:
			encode_request = encode_prompt + record + description_of_change
			encode_response = client.chat.completions.create(model="gpt-4-1106-preview",
			messages=[{"role": "user", "content": encode_request}])
			update = encode_response.choices[0].message.content
			return update
		except Exception:
			return None
