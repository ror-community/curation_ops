import sys
import csv
import re
import os
import urllib.parse
from time import sleep
from collections import defaultdict
import pyautogui
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import TimeoutException

driver = webdriver.Firefox()
already_clicked = []


def fill_primary_metadata(org_data):
    form_ids = {'name': '#/properties/name-input',
                'established': '#/properties/established-input',
                'wikipedia_url': '#/properties/wikipedia_url-input',
                'aliases': '#/properties/aliases-input',
                'acronyms': '#/properties/acronyms-input',
                            'links': '#/properties/links-input'}
    for key in form_ids.keys():
        if org_data[key] is not None:
            if isinstance(org_data[key], list):
                for value in org_data[key]:
                    input_field = driver.find_element(By.ID, form_ids[key])
                    input_field.send_keys(value)
                    input_field.send_keys(Keys.RETURN)
                    sleep(1)
            else:
                input_field = driver.find_element(By.ID, form_ids[key])
                input_field.send_keys(org_data[key])
                input_field.send_keys(Keys.RETURN)
                sleep(1)


def click_off():
    right_column = driver.find_element(
        By.CSS_SELECTOR, "div[class='col col-4']")
    right_column.click()


def select_org_type(org_type):
    type_dropdown = driver.find_element(
        By.CSS_SELECTOR, "div[class='v-select__selections']")
    type_dropdown.click()
    sleep(1)
    org_type_xpath = '//div[contains(text(), "' + org_type + '")][contains(@class,"v-list-item__title")]'
    org_type_selection = driver.find_element(By.XPATH, org_type_xpath)
    org_type_selection.click()
    sleep(1)
    click_off()
    sleep(1)


def add_label(label_index, label, label_lang):
    label_index += 1
    add_label_button = driver.find_element(
        By.CSS_SELECTOR, "button[aria-label='Add to Labels']")
    add_label_button.click()
    sleep(2)
    label_button_xpath = '//span[contains(text(), "' + str(
        label_index) + '")][contains(@class,"info--text text--lighten-5")]'
    label_button = driver.find_element(
        By.XPATH, label_button_xpath)
    already_clicked.append(label_button)
    label_button.click()
    sleep(2)
    if label_index == 2:
        label_input_field = driver.find_element(
            By.ID, '#/properties/label' + str(label_index) + '-input')
        label_lang_field = driver.find_element(
            By.ID, '#/properties/iso639' + str(label_index) + '-input')
    else:
        label_input_field = driver.find_element(
            By.ID, '#/properties/label-input')
        label_lang_field = driver.find_element(
            By.ID, '#/properties/iso639-input')
    label_input_field.click()
    label_input_field.send_keys(label)
    sleep(2)
    label_lang_field.click()
    sleep(2)
    label_lang_field.send_keys(label_lang)
    label_lang_xpath = '//span[contains(text(), "' + label_lang + '")][contains(@class,"v-list-item__mask")]'
    label_lang_selection = driver.find_element(By.XPATH, label_lang_xpath)
    label_lang_selection.click()
    click_off()
    sleep(3)


def fill_address(geonames_id):
    driver.execute_script("window.scrollTo(0, window.scrollY + 4000)")
    add_address_button = driver.find_element(
        By.CSS_SELECTOR, "button[aria-label='Add to Addresses']")
    add_address_button.click()
    sleep(2)
    num_one_button_xpath = '//span[contains(text(), "1")][contains(@class,"info--text text--lighten-5")]'
    all_num_one_buttons = driver.find_elements(
        By.XPATH, num_one_button_xpath)
    real_address_button = [
        b for b in all_num_one_buttons if b not in already_clicked][0]
    real_address_button.click()
    sleep(2)
    geonames_input_field = driver.find_element(
        By.ID, '#/properties/geonames_city/properties/id-input')
    geonames_input_field.click()
    geonames_input_field.send_keys(geonames_id)
    sleep(1)
    click_off()
    sleep(2)
    driver.execute_script("window.scrollTo(0, window.scrollY + 4000)")


def add_external_identifiers(identifier_type, identifier_value):
    identifier_type_tab_forms = {
        'isni': 'ISNI', 'wikidata': 'Wikidata', 'fundref': 'FundRef', 'grid': 'GRID'}
    identifier_type = identifier_type_tab_forms[identifier_type]
    driver.execute_script("window.scrollTo(0, window.scrollY + 4000)")
    tab_xpath = '//div[contains(text(), "' + identifier_type + '")]'
    id_input_tab = WebDriverWait(driver, 3).until(
        expected_conditions.element_to_be_clickable((By.XPATH, tab_xpath)))
    driver.execute_script("arguments[0].click();", id_input_tab)
    sleep(2)
    try:
        preferred_input_field_id = '#/properties/external_ids/properties/' + \
            identifier_type + '/properties/preferred-input'
        preferred_input_field = WebDriverWait(driver, 3).until(
            expected_conditions.element_to_be_clickable((By.ID, preferred_input_field_id)))
        driver.execute_script("arguments[0].click();", preferred_input_field)
        preferred_input_field.send_keys(identifier_value)
        all_input_field_id = '#/properties/external_ids/properties/' + \
            identifier_type + '/properties/all-input'
        all_input_field = driver.find_element(By.ID, all_input_field_id)
        driver.execute_script("arguments[0].click();", all_input_field)
        all_input_field.send_keys(identifier_value)
        sleep(1)
    except TimeoutException:
        preferred_input_field_id = '#/properties/preferred-input'
        preferred_input_field = WebDriverWait(driver, 3).until(
            expected_conditions.element_to_be_clickable((By.ID, '#/properties/preferred-input')))
        driver.execute_script("arguments[0].click();", preferred_input_field)
        preferred_input_field.send_keys(identifier_value)
        all_input_field_id = '#/properties/all-input'
        all_input_field = driver.find_element(By.ID, all_input_field_id)
        driver.execute_script("arguments[0].click();", all_input_field)
        all_input_field.send_keys(identifier_value)
        sleep(1)


def download_file():
    download_xpath = "//span[contains(text(), 'Download')]"
    download_button = driver.find_element(By.XPATH, download_xpath)
    download_button.click()
    sleep(3)
    # Specific to local instance of Firefox. Update to accomodate your download modal.
    pyautogui.moveTo(485, 548)
    pyautogui.click()
    pyautogui.press('enter')


def convert_field_to_list(data):
    if ';' in data:
        data = data.split(';')
        data = [d.strip() for d in data]
        return data
    else:
        return [data]


def parse_csv(f):
    csv_orgs = []
    prepared_orgs = []
    with open(f, encoding='utf-8-sig') as f_in:
        reader = csv.DictReader(f_in)
        data_fields = reader.fieldnames
        for row in reader:
            null = None
            entry = {}
            for field in data_fields:
                if row[field] != '':
                    entry[field] = row[field].strip()
                else:
                    entry[field] = null
            csv_orgs.append(entry)
    for org in csv_orgs:
        if org['name'] is None or org['types'] is None or org['geonames_id'] is None:
            print('Insufficient data for org:', org)
            sys.exit()
        repeating_fields = ['aliases', 'acronyms', 'types']
        for repeating_field in repeating_fields:
            if org[repeating_field] is not None:
                org[repeating_field] = convert_field_to_list(
                    org[repeating_field])
        if org['wikipedia_url'] is not None:
            org['wikipedia_url'] = urllib.parse.unquote(org['wikipedia_url'])
        labels = org['labels']
        if labels is not None:
            if ';' in labels:
                all_labels = []
                labels = labels.split(';')
                labels = [label.strip() for label in labels]
                for label in labels:
                    label = label.split('*')
                    label_name, label_lang = label[0], label[1]
                    label_dict = {'label': label_name,
                                  'iso639': label_lang}
                    all_labels.append(label_dict)
                org['labels'] = all_labels
            else:
                labels = labels.split('*')
                label_name, label_lang = labels[0], labels[1]
                label_dict = {'label': label_name, 'iso639': label_lang}
                org['labels'] = [label_dict]

        prepared_orgs.append(org)

    return prepared_orgs


def create_record(org_data):
    external_identifers = ['isni', 'grid', 'wikidata', 'fundref']
    # ROR Record editor URL
    driver.get('https://leo.dev.ror.org')
    sleep(3)
    driver.find_element(By.ID, "#new").click()
    sleep(3)
    fill_primary_metadata(org_data)
    select_org_type(org_data['types'][0])
    org_labels = org_data['labels']
    if org_labels != None:
        for i, org_label in enumerate(org_labels):
            add_label(i, org_label['label'], org_label['iso639'])
    fill_address(org_data['geonames_id'])
    for external_identifier in external_identifers:
        if org_data[external_identifier] != None:
            add_external_identifiers(
                external_identifier, org_data[external_identifier])
    download_file()


if __name__ == '__main__':
    records = parse_csv(sys.argv[1])
    for record in records:
        create_record(record)
