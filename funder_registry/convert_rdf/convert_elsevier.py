import os
import re
import csv
import sys
import glob
from bs4 import BeautifulSoup

def not_none(labels):
    if labels != []:
        labels = '; '.join(labels)
        return labels
    return None

def convert_records(f):
    with open(f, 'r') as f:
        data = f.read()
    soup = BeautifulSoup(data, "xml")
    records = []
    concepts = soup.find_all('skos:Concept')
    for concept in concepts:
        funder_id = concept['rdf:about']
        name = concept.find('skosxl:prefLabel').find(
            'skosxl:Label').find('skosxl:literalForm').text
        statuses = concept.find_all('rdf:type')
        if statuses is not None:
            if len(statuses) == 1:
                status = statuses[0]['rdf:resource']
                status = re.sub(
                    'http://data.elsevier.com/vocabulary/SciValFunders/FBstatus/', '', status)
            else:
                status = ';'.join([re.sub(
                    'http://data.elsevier.com/vocabulary/SciValFunders/FBstatus/', '', status['rdf:resource']) for status in statuses])
        replaced_by = concept.find('dct:isReplacedBy')
        if replaced_by is not None:
            replaced_by = replaced_by['rdf:resource']
        renamed_as = concept.find('renamedAs')
        if renamed_as is not None:
            renamed_as = renamed_as['rdf:resource']
        alt_labels = concept.find_all('skosxl:altLabel')
        aliases = []
        acronyms = []
        abbrev_names = []
        if alt_labels != None:
            for alt_label in alt_labels:
                usage_flag = alt_label.find('emst:usageFlag')
                if usage_flag is not None:
                    if 'Acronym' in usage_flag['rdf:resource']:
                        acronyms.append(alt_label.find('skosxl:Label').find('skosxl:literalForm').text)
                    elif 'abbrevName' in usage_flag['rdf:resource']:
                        abbrev_names.append(alt_label.find('skosxl:Label').find('skosxl:literalForm').text)
                else:
                    aliases.append(alt_label.find('skosxl:Label').find('skosxl:literalForm').text)
        aliases, acronyms, abbrev_names = not_none(aliases), not_none(acronyms), not_none(abbrev_names)
        funding_type = concept.find('fundingBodyType')
        if funding_type is not None:
            funding_type = funding_type.text
        funding_subtype = concept.find('fundingBodySubType')
        if funding_subtype is not None:
            funding_subtype = funding_subtype.text
        tax_id = concept.find('taxId')
        if tax_id is not None:
            tax_id = tax_id.text
        region = concept.find('region')
        if region is not None:
            region = region.text
        state_geonames_id = concept.find('state')
        if state_geonames_id is not None:
            state_geonames_id = state_geonames_id['rdf:resource']
        country_code = concept.find('schema:address').find(
            'schema:postalAddress').find('schema:addressCountry').text
        country_geonames_id = concept.find('country')
        if country_geonames_id is not None:
            country_geonames_id = country_geonames_id['rdf:resource']
        affiliated_with = concept.find('affilWith')
        if affiliated_with is not None:
           affiliated_with = affiliated_with['rdf:resource']
        narrower = concept.find_all('skos:narrower')
        if narrower is not None:
            narrower = '; '.join([narrow['rdf:resource']
                                  for narrow in narrower])
        broader = concept.find_all('skos:broader')
        if narrower is not None:
            broader = '; '.join([broad['rdf:resource'] for broad in broader])
        continuation_of = concept.find('continuationOf')
        if continuation_of != None:
            continuation_of =  continuation_of['rdf:resource']
        created = concept.find('dct:created')
        if created is not None:
            created = created.text
        modified = concept.find('dct:modified')
        if modified is not None:
            modified = modified.text
        records.append([funder_id, name, status, aliases, acronyms, abbrev_names, funding_type, funding_subtype, tax_id, region, country_code,
                        country_geonames_id, state_geonames_id, affiliated_with, narrower, broader, continuation_of, replaced_by, renamed_as, created, modified])
    return records


def parse_files():
	for rdf_file in glob.glob('*.rdf'):
	    outfile = rdf_file.split('.rdf')[0] + '.csv'
	    header = ['funder_id', 'name', 'status', 'aliases', 'acronyms', 'abbrev_names','funding_type', 'funding_subtype', 'tax_id','region',
	              'country_code', 'country_geonames_id', 'state_geonames_id', 'affiliated_with', 'narrower', 'broader', 'continuation_of', 'replaced_by', 'renamed_as', 'created', 'modified']
	    with open(outfile, 'w') as f_out:
	        writer = csv.writer(f_out)
	        writer.writerow(header)
	    records = convert_records(rdf_file)
	    for record in records:
	        with open(outfile, 'a') as f_out:
	            writer = csv.writer(f_out)
	            writer.writerow(record)


if __name__ == '__main__':
    parse_files()
