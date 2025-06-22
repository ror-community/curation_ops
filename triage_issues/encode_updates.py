import os
import re
import requests
import signal
from contextlib import contextmanager
from google import genai

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')


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
	if not GEMINI_API_KEY:
		print("Error: GEMINI_API_KEY is not set. Cannot encode update.")
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
			client = genai.Client(api_key=GEMINI_API_KEY)
		except Exception as e:
			print(f"Error creating Gemini client: {e}")
			return None
		
		try:
			encode_request = encode_prompt + record + description_of_change
			with time_limit(120):
				encode_response = client.models.generate_content(
					model='gemini-2.5-pro',
					contents=encode_request
				)
				update = encode_response.text
				return update
		except TimeoutError as e:
			print(f"Gemini API call timed out: {e}")
			return None
		except Exception as e:
			print(f"An error occurred with the Gemini API: {e}")
			return None
	else:
		print(f"Failed to fetch ROR record for {ror_id}. Status code: {r.status_code}")
		return None
