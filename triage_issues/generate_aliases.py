import os
import re
import requests
import signal
from contextlib import contextmanager
from google import genai


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

def generate_aliases(new_record_request):
	generate_prompt ="""
	You are an AI assistant trained on large volumes of scholarly research. Your task is to provide additional variant names, variant spellings, other name forms associated with an organization. Your list of variant names does not include short initialisms or abbreviations. 

	As input, you will receive a labeled description of the organization. This will provide you with contextual information about what organization is being referred to, as well as the existing variant names identified by the user. You will then process this information with a series of tasks to return the list of variant names. For example, if provide the labeled description:

	"Summary of request: Add a new organization to ROR

	Name of organization: Academia Paedagogica Cracoviensis
	Website: 
	Link to publications: 
	Organization type: Education
	Wikipedia page:
	Wikidata ID:
	ISNI ID: 0000 0001 2113 3716
	GRID ID:
	Crossref Funder ID:
	Other names for the organization: 
	Acronym/abbreviation:
	Related organizations: 
	City: Krakow
	Country: Poland
	Geonames ID: 
	Year established:
	How will a ROR ID for this organization be used? 
	Other information about this request:"

	You would:

	    1. Extract information from the provided input: Identify the main organization name, country, city, and any related organizations or acronyms/abbreviations already provided in the input.

	    2. Language identification: Determine the language(s) in which the organization's name is written, based on the provided names, city, and country.

	    2. Identify similar organizations in your training data: Search your training data for organizations with similar names, locations, or types, as well as any known authoritative sources or citations that mention them. Take note of any alternative names, spellings, or translations you find.

	    4. Identify patterns and variations: Based on the information collected in step 3, identify common patterns and variations in the organization's name. This may include changes in word order, abbreviations, or different ways to express the same concept (e.g., "University" vs. "Academy").

		    4.1. Look for patterns in the native language: Identify common naming conventions, abbreviations, and variations in the organization's native language.

		    4.2. Look for patterns in English and other languages: Identify common naming conventions, abbreviations, and variations in English and other languages relevant to the organization's location.

	    5. Generate additional variants: Use the patterns and variations identified in step 4 to create additional variant names and spellings not already found in the existing record. Consider different combinations of words, abbreviations, and translations, as well as variations in the use of the organization's name in different languages.

		    5.1. Generate variants in the native language: Create alternative names and spellings based on the patterns identified in the organization's native language.

		    5.2. Generate variants in English and other languages: Create alternative names and spellings based on the patterns identified in English and other relevant languages.

	    6. Remove sub-unit entities, duplicates, short initialisms/abbreviations:
		    6.1. Identify sub-unit entities:
		    6.1.1. Review the list of variant names generated in step 5.
		    6.1.2. Look for names that refer to sub-units, departments, or specific research centers within the organization, rather than the organization as a whole.
		    6.1.3. Remove any sub-unit entities from the list.

		    6.2. Remove duplicates:
		    6.2.1. Compare each name on the list to every other name.
		    6.2.2. Identify names that are identical or very similar (e.g., differences only in capitalization or punctuation).
		    6.2.3. Remove duplicate or near-duplicate names, retaining only one instance of each unique name.

		    6.3. Remove short initialisms/abbreviations:
		    6.3.1. Examine each name on the list for short initialisms or abbreviations (e.g., acronyms with three or fewer characters).
		    6.3.2. Check whether these short initialisms or abbreviations were excluded from the original request.
		    6.3.3. Remove any short initialisms or abbreviations that were excluded from the original request.

	    7. Quality check:
		    7.1. Review the final list of variant names for plausibility:
		    7.1.1. Examine each name on the list to ensure it is a plausible representation of the organization's name.
		    7.1.2. Check that the names follow the patterns, conventions, and variations identified in steps 1-6.
		    7.1.3. Remove any implausible or nonsensical names from the list.

		    7.2. Ensure accuracy based on the information gathered in steps 1-6:
		    7.2.1. Compare the variant names to the main organization name and any related organizations, acronyms, or abbreviations provided in the original request.
		    7.2.2. Verify that the variant names align with the organization's name, location, and type.
		    7.2.3. Remove any names that do not accurately represent the organization or are abbreviations, acronyms, or short initialisms.

		    7.3. Check for duplication with the original request:
		    7.3.1. Compare the variant names to the names provided in the original request.
		    7.3.2. Identify any names that are identical or very similar to those in the original request (e.g., differences only in capitalization or punctuation).
		    7.3.3. Remove any duplicate or near-duplicate names that match those provided in the original request.

	and return the following list of variant names in a string representation of a python list:


	Academia Paedagogica Cracoviensis
	Academia Paedagogicae Cracoviensis
	Akademia Pedagogiczna
	Akademia Pedagogiczna Im. KEN Kraków
	Akademia Pedagogiczna Im. Komisji Edukacji Narodowej Kraków
	Akademia Pedagogiczna im. Komisji Edukacji Narodowej w Krakowie
	Akademia Pedagogiczna Imienia Komisji Edukacji Narodowej Kraków
	Akademia Pedagogiczna imienia Komisji Edukacji Narodowej w Krakowie
	Akademia Pedagogiczna Kraków
	Pedagogical Academy of Cracow of the National Education Commission
	Pedagogical University of Cracow
	Pedagogical University of Cracow of the National Education Commission
	Polish Academy of Educational Sciences
	Uniwersytet Pedagogiczny im Komisji Edukacji Narodowej w Krakowie
	Wyzsza Szkola Pedagogiczna im. Edukacji Narodowej w Krakowie

	Now, provide the list of variant names for the following organization. Respond only with list of names, one name on each line, with no other text:
	"""
	try:
		client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))
		generate_request = generate_prompt + new_record_request
		with time_limit(120):
			generate_response = client.models.generate_content(
				model='gemini-2.5-pro',
				contents=generate_request
			)
			aliases = generate_response.text
			aliases = [alias.strip() for alias in aliases.split('\n') if not alias.isupper()]
			return aliases
	except TimeoutError as e:
		print(f"GenAI API call timed out: {e}")
		return None
	except Exception as e:
		print(f"Error generating aliases: {e}")
		import traceback
		traceback.print_exc()
		return None
