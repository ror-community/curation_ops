# Curation Ops


# Requests

Requests are submitted via a Google Form linked on the [ROR site](https://ror.org/contact/). On submission, they are saved into a Google Sheet and converted into Github issues in the [ror-updates](https://github.com/ror-community/ror-updates) repository using Zapier.

# Triage

By default, submitted requests are lumped into two categories: new and update requests. Each request type has an associated [issue template](https://github.com/ror-community/ror-updates/tree/master/.github/ISSUE_TEMPLATE) with corresponding fields to which the user-submitted metadata is mapped. By default, these issues are assigned to the Metadata Curation Lead.

# Initial Triage

Submitted metadata should be reviewed, corrected and parsed to conform with ROR’s metadata policies. Metadata from these issues is extracted programmatically to create new and updated records. Although the metadata undergoes additional review at time of extraction, having it correctly represented in the issues is important to reduce the time and overall work needed to prepare the release in which it will be included.

# Triage Tool

All new and update requests should be checked with the [triage tool](https://github.com/adambuttrick/triage_tool). The triage tool queries Wikidata, ORCID, Crossref, as well as the ROR and Github APIs for duplicate requests. The metadata it returns is generally only useful for populating fields in new record requests, but the tool should still be used for update requests to make sure that a given request has not been previously submitted.

# Coding New Records

In all issues, repeating fields should have their instances of the field separated with semicolons. For example, if a new record request has three aliases submitted, they should be represented in the aliases field as follows: 

        alias_1; alias_2; alias_3

Labels must additionally be appended with an asterisk and the name of their language for each label instance. For example, if a record had a Spanish and German label, it would be represented in the labels field as follows: 

        Spanish_label*Spanish; Japanese_label*Japanese

Relationships should be represented in the relationships field using the following pattern: ror_id (relationship_type). There is no need to separate repeating instances of the relationships with semicolons, but each must be followed by the relationship type value in order to be extracted. For example, record for which three relationships needed to be added would be coded in the relationships field as follows:

        https://ror.org/000000001 (parent) https://ror.org/000000002 (child) https://ror.org/000000003 (related)


# Coding Update Records

Update records are coded with an “Update:” field, changes to specified fields separated by semicolons, and terminated with a “$”. Each change has one of four possible types, change, add, delete, and replace, the name of the field as it exists in the [schema](https://github.com/ror-community/ror-schema/blob/master/ror_schema.json), followed by two equals signs (“==”), and then the value to be changed. “Change” updates the value in non-repeating fields to that supplied. “Add” and “delete” will add or delete the corresponding values from a repeating field, while “replace” will replace whatever data exists in a field with that being supplied. “Replace” should only be used where one wishes to update a repeating field where a single value is currently present that you wish to replace with another, or to wipe all its data and replace it with a single value. When adding new labels, the must again be appended with an asterisk and the name of their language for each label instance. This is not necessary for deleting them. 

Putting this altogether, if we wished to change an organization’s name, delete an alias, add a label, and replace it’s ISNI, it would be coded as follow:

        Update: change.name==New Name; delete.aliases==Alias to Delete; add.labels== New Label*Language; replace.ISNI==ISNI_ID;$

# Approval/Denial of Requests

Requests are approved and denied using the [Curator Evaluation Workflows](https://github.com/ror-community/ror-updates/wiki) for new and update record requests. All new record requests require an additional confirmation of their approvals/denials by the curation team and so should be moved to the Second Review project column after being triaged. Update requests that can be immediately verified by the Metadata Curation Lead can be approved without secondary review and moved to the Ready for Sign Off project column. More complex updates should undergo additional review by the curation team. 

Every three weeks, a summary report of outstanding issues to be reviewed should be sent by the Metadata Curation Lead to the curation team. This report should identify outstanding requests by their relative complexity, specifically differentiating between requests that simply need a secondary approval/denial and those that require further consideration and review.


# Preparing Requests for Metadata Extraction

Requests that have been approved and moved to the "Ready for sign off/metadata QA" column should have their metadata verified for correctness/completion. Verify that all fields correspond to that of the organization, changes mentioned in the comments of the issue are reflected in its main body, relationships are properly represented, and links (including those to external identifiers), resolve. Once the metadata in the request has been verified, it should be moved to the Approved column.

# Github Personal Access Token

For the next steps, a Github personal access token with full repo and admin:org permissions must be [generated](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token) and added to each of the named scripts. The same token can be used for all. Make certain that you do not commit these values back into the curation repository.

# Extracting Metadata

The metadata for creating new and update records is extracted via the Github API via two separate scripts: [get_new_records.py](https://github.com/ror-community/curation_scripts/tree/main/automate_new_records) and [get_update_records.py](https://github.com/ror-community/curation_scripts/tree/main/automate_record_updates). For their metadata to be extracted, the new and update record requests must reside in the Approved column. In addition, a Github personal access token must be added to the scripts.

Both scripts return CSV files containing the metadata for the new and update records.


# Reviewing Extracted Metadata

The new and updates records’ CSVs should be imported into Excel for review. 

For the new records metadata: 
* Examine all entries for completeness of mandatory fields (name, type, Geonames ID).
* Check any missing fields against their corresponding issues to verify the completeness of extraction.
* Delete corporate suffixes (LLC, GmbH, Inc, etc) from the names field.
* Where the primary name is not English, examine the labels and aliases fields for English named. 
  * If an English form exists, check issue to see whether a non-English primary name was required by the organization. 
  * If no such requirement exists, switch the English name to the primary field and the current name to a label.
* Check repeating fields to verify that that each instance of the field is separated with semicolons. 
* Make sure that all labels have a language assigned. 
* Verify that aliases and labels are properly distinguished from one another.
* Verify that entries in the acronyms field are all properly represented and do not contain aliases or labels.
* Use Excel’s conditional formatting to highlight instances of duplicate fields and remove duplicate entries as needed. Update/close issues correspondingly.


For update records, make sure that all entries have update codings. Spot check 10-20 entries at random and verify that the coding corresponds to the changes in described in the request.


Once you have complete review of the new and update records, provide your updated versions of both files to another ROR team member for review. After their review is complete, save both the new and updates metadata files in CSV format. Check both files for unprintable characters using the [unprintable_csv_check.py](https://github.com/ror-community/curation_scripts/tree/main/unprintable_csv) and update the CSVs accordingly.

# Creating New and Update records

New and updated records are created with two scripts: [create_new_records.py](https://github.com/ror-community/curation_scripts/tree/main/automate_new_records) and [update_records.py](https://github.com/ror-community/curation_scripts/tree/main/automate_record_updates). Both scripts take as inputs CSV files of the format output by [get_new_records.py](https://github.com/ror-community/curation_scripts/tree/main/automate_new_records) and [get_update_records.py](https://github.com/ror-community/curation_scripts/tree/main/automate_record_updates). 

The script for creating new records uses Selenium and Firefox to control Leo. Controlling Firefox with Leo requires installing Mozilla’s [geckodriver utility](https://github.com/mozilla/geckodriver/releases), in addition to the python dependencies in the requirements.txt file. Controlling Leo via Selenium/Firefox requires browser and mouse automation, so your device will be inaccessible until the JSON creation is complete (unless the script it run inside a virtual machine or similar utility).

Update records are created by retrieving the record to be updated from the ROR API, applying changes to the JSON, and saving the update file.

# JSON Checks

After the JSON has been created, it should be checked with a series of scripts in the "tests" directory.

* [new_records_check_integrity.py](https://github.com/ror-community/curation_scripts/tree/main/json_integrity_checks/new_records_check) and [updates_records_check_integrity.py](https://github.com/ror-community/curation_scripts/tree/main/json_integrity_checks/updates_record_check) verify that the JSON files created correspond to the CSVs used to create them. Both scripts take as inputs the CSV files used to generate the JSON, updated to include the JSON file names for each entry. The scripts should be run from inside the directories containing the JSON so that the files for each entry can be opened and read correctly.
* [leading_trailing](https://github.com/ror-community/curation_ops/tree/main/tests/leading_trailing) verifies that there are no leading or trailing punctuation, whitespace, or similar characters in the records. The script is run inside the directory containing the release files.
*  [duplicate_check.py](https://github.com/ror-community/curation_scripts/tree/main/json_integrity_checks/duplicate_values_check) verifies that no values have been repeated in creating the various fields in the JSON.
*  [in_release_duplicate_check.py](https://github.com/ror-community/curation_ops/tree/main/tests/in_release_duplicate_check) and [on_production_duplicate_check](https://github.com/ror-community/curation_ops/tree/main/tests/on_production_duplicate_check) respectively verify that there are no files duplicated in the release and that no files in the release already exist on production. They should both be run in the directory containing the new records for a given release.
* [unprintable_json_check.py](https://github.com/ror-community/curation_scripts/tree/main/unprintable_json) to make sure that no unprintable characters have been included in them.

# Creating the relationships file.

The relationships file can be created using [create_relationships.py](https://github.com/ror-community/curation_scripts/tree/main/create_relationships). To identify related records as being in the release versus production, this script requires as input a CSV the issue URL in a column labeled "html_url", the ROR ID in a column labeled "ror_id", and the name of organization in a column labeled "name." By default, the CSV output by [get_update_records.py](https://github.com/ror-community/curation_scripts/tree/main/automate_record_updates) is formatted like this. For the new records metadata file output by [get_new_records.py](https://github.com/ror-community/curation_scripts/tree/main/automate_new_records), the ROR IDs for the new records must be reconciled with the file and added to it.


# Committing to ror-updates repo


Once the JSON files have been checked for integrity, the files should be committed to [ror-updates](https://github.com/ror-community/ror-updates). For each release, create a branch and corresponding directory on that branch, both named, “rc-vX.X,” where “X.X” corresponds to the release version. Within this directory, create separate directories for the new and update records, labeled “new” and "updates." 

# Git CLI

These steps assume that you have already installed and configured git on your computer, and that you have cloned the ror-updates repository locally.


1.	Create a new branch in the repository with the exact same name as the release (ex, v1.5).

        git checkout -b rc-1.5
        
2.	Create in new directory in the root of the ror-records repository the exact same name as the release (ex, v1.5).

        mkdir rc-1.5

3.	Create new and updates directories inside this directory

        mkdir rc-1.5/new rc-1.5/updates

4.	Place the JSON files for new and update records inside the two directories you just created.

5.	Add and commit the files

        git add rc-1.5/

        git commit -m "add new and updated ROR records in release 1.5 for review"

6.	Push the files to the branch on remote ror-updates repository

        git push origin rc-1.5


# Further Changes to Release JSON

Once the files have been committed to ror-updates any further changes should be made by cloning the repository, changing the files, committing, and pushing them back up to the repo. This will guarantee a single point of reference for the release.

# Adding to Milestone

Once all records for a given release have been identified, they should be added to the release milestone with [add_to_milestone.py](https://github.com/ror-community/curation_scripts/tree/main/add_to_milestone). This script takes as input a CSV file containing the issue numbers for everything to be included in the release, placed in a column labeled "issue_number."


# Testing Staging and Production

Follow the steps outlined in the [ror-records readme](https://github.com/ror-community/ror-records) for publishing the release to both staging and production. At both the staging and production release testing steps, use the [release_tests_staging.py](https://github.com/ror-community/curation_scripts/tree/main/release_tests) and [release_tests_prod.py](https://github.com/ror-community/curation_scripts/tree/main/release_tests) to test the release. Both scripts are ran inside a directory containing all the JSON files included in the release. This is easiest copied from the release branch itself once the files have been committed to [ror-records](https://github.com/ror-community/ror-records). In addition, a text file containing all of the ROR IDs from the previous datadump must be included in this directory. This text file can be generated using the JSON file of the last data dump and [get_all_ror_ids.py](https://github.com/ror-community/curation_scripts/tree/main/all_ror_ids)

During these steps, the data dump for each should be tested as well. Once generated, this file can be tested using [data_dump_test_staging.py](https://github.com/ror-community/curation_scripts/tree/main/data_dump_tests) and [data_dump_test_prod.py](https://github.com/ror-community/curation_scripts/tree/main/data_dump_tests). Both scripts are likewise ran inside a directory containing all the JSON files included in the release and require that you add the filepath for the data dump from the prior release to them.


