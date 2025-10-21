import os
import re
import signal
import requests
from contextlib import contextmanager

import openai

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-5')


class TimeoutError(Exception):
	pass


@contextmanager
def time_limit(seconds):
	def signal_handler(signum, frame):
		raise TimeoutError(f"Process timed out after {seconds} seconds")
	signal.signal(signal.SIGALRM, signal_handler)
	signal.alarm(seconds)
	try:
		yield
	finally:
		signal.alarm(0)


def encode_update(ror_id, description_of_change):
	if not OPENAI_API_KEY:
		print("Error: OPENAI_API_KEY is not set. Cannot encode update.")
		return None
	
	script_dir = os.path.dirname(os.path.abspath(__file__))
	prompt_file_path = os.path.join(script_dir, "encode_prompt.txt")
	ror_api_url = 'https://api.ror.org/v2/organizations/' + ror_id
	r = requests.get(ror_api_url)
	if r.status_code == requests.codes.ok:
		with open(prompt_file_path, 'r', encoding="utf-8") as file:
			encode_prompt = file.read()
		record = str(r.json())
		try:
			client = openai.OpenAI(api_key=OPENAI_API_KEY)
		except Exception as e:
			print(f"Error creating OpenAI client: {e}")
			return None
		
		try:
			encode_request = encode_prompt + record + description_of_change
			with time_limit(120):
				encode_response = client.responses.create(
					model=OPENAI_MODEL,
					input=encode_request
				)
				update_text = getattr(encode_response, "output_text", None)
				if not update_text:
					update_chunks = []
					for output in getattr(encode_response, "output", []) or []:
						for content in getattr(output, "content", []) or []:
							if getattr(content, "type", None) == "output_text" and getattr(content, "text", None):
								update_chunks.append(content.text)
					update_text = "".join(update_chunks).strip() if update_chunks else None
				if update_text:
					return update_text
				print("OpenAI API returned no text content.")
				return None
		except TimeoutError as e:
			print(f"OpenAI API call timed out: {e}")
			return None
		except Exception as e:
			print(f"An error occurred with the OpenAI API: {e}")
			return None
	else:
		print(f"Failed to fetch ROR record for {ror_id}. Status code: {r.status_code}")
		return None
