#!/usr/bin/python3
# encoding: utf-8

import bs4
import csv
from datetime import datetime
import os
import re
import requests
from time import sleep

DISTRICTS = {
             "Eixample": [
                 "El Fort Pienc",
                 "L'Antiga Esquerra de l'Eixample",
                 "La Dreta de l'Eixample",
                 "La Nova Esquerra de l'Eixample",
                 "La Sagrada Família",
                 "Sant Antoni"
                 ],
             "Les Corts": [
                 "Les Corts",
                 "Pedralbes"
                 ],
             "Sant Martí": [
                 "El Clot", "El Parc i la Llacuna del Poblenou",
                 "El Poblenou", "La Vila Olímpica del Poblenou",
                 "Provençals del Poblenou"
                 ],
             "Sants-Montjuïc": [
                 "Hostafrancs",
                 "Sants"
                 ],
             "Sarrià-Sant Gervasi": [
                 "Les Tres Torres", "Sarrià",
                 "Sant Gervasi-Galvany",
                 "Sant Gervasi-La Bonanova"
                 ]
            }
PRICE_VARIATIONS_FILE = "Idealista_Price_Variations.csv"
RECORD_FILE = "Idealista_Apts_Record.csv"
RETIRED_APTS_FILE = "Idealista_Retired_Apts.csv"
RECORDS_ACCOUNTING_FILE = 'Idealista_Records_Accounting.csv'


def record_new_apts_in_districts_and_subdistricts():
    for district, subdistricts_list in DISTRICTS.items():
        # Control print
        print('\nDISTRICT: ' + district.upper())

        for subdistrict in subdistricts_list:
            # Control print
            print('\n SUBDISTRICT: ' + subdistrict.upper() + '\n')

            get_late_subdistrict_apts_info(district,
                                           subdistrict)


def get_late_subdistrict_apts_info(district, subdistrict):
    apt_number = 0  # Control print

    for i in range(1, 100):
        r = requests.get('https://www.idealista.com/es/alquiler-viviendas/\
barcelona/' + ascii_converter(district) + '/' + ascii_converter(subdistrict) +
                         '/pagina-' + str(i) + '.htm')

        try:
            r.raise_for_status()
        except Exception as exc:
            print("There was a problem: %s" % (exc))

        page_text = r.text.encode('utf-8').decode('utf-8', 'ignore')
        soup = bs4.BeautifulSoup(page_text, 'html.parser')

        apt = soup.find_all("div", class_="item")
        if len(apt) == 0:
            break

        print ('\n::PAGE ' + str(i) + '::\n')  # Control print

        j = 0
        next_index_exists = True
        while next_index_exists is True:
            apt_info = []
            apt_partial_link = ''
            apt_id = ''
            apt_link = ''
            apt_title = ''
            apt_price_text = ''
            apt_price = ''
            apt_details_list = []
            apt_details_string = ''
            apt_size_text = ''
            apt_size = ''
            apt_details = ''
            apt_short_description = ''

            try:
                apt_partial_link = apt[j].find(
                    class_='item-link ')["href"]
                apt_id = apt_partial_link.split('/')[2]
                apt_link = 'https://www.idealista.com' +\
                           apt_partial_link
            except AttributeError:
                pass

            try:
                apt_title = apt[j].find(class_='item-link ').get_text()
            except AttributeError:
                pass

            try:
                apt_price_text = apt[j].find(class_='item-price').get_text()
                apt_price = re.sub("€/mes", '', apt_price_text)
            except AttributeError:
                pass

            try:
                for element in apt[j].find_all(
                                    'span', attrs={
                                        'class': 'item-detail'}):
                    if apt_details_list != []:
                        apt_details_list.append(', ')
                    apt_details_list.append(element.get_text())
                apt_details_string = ''.join(apt_details_list)

                apt_size_text = re.compile(
                               r'\d+ m²').findall(
                                              apt_details_string)[0]
                apt_size = re.sub(" m²", '', apt_size_text)

                apt_details = re.sub('\d+ m²',
                                     '',
                                     apt_details_string).\
                    replace(' , ', ' ').lstrip(',').lstrip(', ').\
                    rstrip(',').rstrip(', ')

            except AttributeError:
                pass

            try:
                apt_short_description = apt[j].find(
                                            class_='ellipsis'
                                            ).get_text()
            except AttributeError:
                pass

            apt_info = [apt_id,
                        apt_title,
                        apt_price,
                        apt_size,
                        apt_details,
                        apt_link,
                        apt_short_description]

            update_record_file(district,
                               subdistrict,
                               *apt_info)

            j += 1
            try:
                apt_partial_link = apt[j].find(class_='item-link ')["href"]
            except IndexError:
                next_index_exists = False

            # Control print
            print(apt_id, ' APT ' + str(j+1+apt_number), '\n',
                  apt_title, '\n',
                  apt_price, '\n',
                  apt_size, '\n',
                  apt_details, '\n',
                  apt_link, '\n',
                  apt_short_description)

        sleep(10)  # Pause to avoid server's max number of retries

        apt_number += j  # Control print


def update_record_file(district, subdistrict, *apt_info):
    global already_registered_apts
    global decreased_price_apts
    global increased_price_apts
    global new_apts
    apt_id = apt_info[0]
    apt_price = apt_info[2]
    apt_link = apt_info[5]

    last_records_list.extend([apt_id])

    existing_apt = False
    with open(RECORD_FILE, 'r', encoding='utf-8') as record_file:
        record_file_reader = csv.DictReader(record_file)
        for record_row in record_file_reader:
            if (apt_id == record_row["ID"]) and\
               (int(apt_price.replace('.', '')) ==
               int(record_row["PRICE (€/month)"].replace('.', ''))):
                already_registered_apts += 1
                print('\n-- PASS --')  # Control print
                print('\n====================\n')  # Control print
                return

            else:
                if (apt_id == record_row["ID"]) and\
                   (apt_price != record_row["PRICE (€/month)"]):
                    existing_apt = True
                    if int(apt_price.
                           replace('.', '')) < int(record_row[
                                                       "PRICE (€/month)"
                                                        ].replace('.', '')):
                        decreased_price_apts += 1
                    else:
                        increased_price_apts += 1
                    print('\n-- PRICE VARIATION --')  # Control print
                    print('\n=====================\n')  # Control print

                    if record_row["PRICE VARIATION"] == 'False':
                        price_variation_info = [
                                        record_row["ID"],
                                        district,
                                        subdistrict,
                                        record_row["DATE"],
                                        record_row["PRICE (€/month)"],
                                        record_row["LINK"]]
                        price_variations_list.append(price_variation_info)

                    price_variation_info = [
                                        apt_id,
                                        district,
                                        subdistrict,
                                        datetime.now().date(),
                                        apt_price,
                                        apt_link]
                    price_variations_list.append(price_variation_info)

                    delete_outdated_apt_info(apt_id)

                    break

    new_apts += 1
    print('\n--  NEW ADDITION  --')  # Control print
    print('\n====================\n')  # Control print
    collect_new_additions(
                      district,
                      subdistrict,
                      existing_apt,
                      *apt_info)


def delete_outdated_apt_info(apt_id):
    outdated_destination_file = RECORD_FILE.split('.')[0] +\
                                   '_(outdated).csv'
    os.rename(os.path.join(os.getcwd(), RECORD_FILE),
              os.path.join(os.getcwd(), outdated_destination_file))

    create_record_file()

    with open(outdated_destination_file, 'r', encoding='utf-8')\
            as outdated_record:
        outdated_record_reader = csv.DictReader(outdated_record)
        with open(RECORD_FILE, 'a', encoding='utf-8')\
                as updated_record:
            updated_record_writer = csv.writer(updated_record)
            for row in outdated_record_reader:
                if row["ID"] != apt_id:
                    outdated_record_row = []
                    for column in row:
                        outdated_record_row.extend(
                            [row[column]]
                            )
                    updated_record_writer.writerow(outdated_record_row)

    os.remove(outdated_destination_file)


def collect_new_additions(
                      district,
                      subdistrict,
                      existing_apt,
                      *apt_info):
    apt_info_with_price_variation_and_date = list(apt_info)
    apt_info_with_price_variation_and_date.insert(3, str(existing_apt))
    apt_info_with_price_variation_and_date.insert(6, datetime.now().date())

    with open(RECORD_FILE, 'a', encoding='utf-8') as writing_file:
        writing_file_writer = csv.writer(writing_file)
        writing_file_writer.writerow(
                                     [district,
                                      subdistrict] +
                                     apt_info_with_price_variation_and_date)


def update_price_variations_file():
    if price_variations_list:
        if not os.path.exists(os.path.join(
                                        os.getcwd(),
                                        PRICE_VARIATIONS_FILE)):
            create_price_variations_file()

        with open(PRICE_VARIATIONS_FILE, 'a', encoding='utf-8')\
                as price_variations:
            price_variations_writer = csv.writer(price_variations)
            for record in price_variations_list:
                price_variations_writer.writerow(record)


def remove_retired_apts():
    global removed_apts

    outdated_destination_file = RECORD_FILE.split('.')[0] +\
        '_(outdated).csv'
    os.rename(os.path.join(os.getcwd(), RECORD_FILE),
              os.path.join(os.getcwd(), outdated_destination_file))

    create_record_file()

    with open(outdated_destination_file, 'r', encoding='utf-8')\
            as outdated_record:
        outdated_record_reader = csv.DictReader(outdated_record)

        for outdated_row in outdated_record_reader:
            if outdated_row["ID"] in last_records_list:
                outdated_record_row = []
                for column in outdated_row:
                    outdated_record_row.extend(
                            [outdated_row[column]]
                            )
                with open(RECORD_FILE, 'a', encoding='utf-8')\
                        as record_file:
                    record_file_writer = csv.writer(record_file)
                    record_file_writer.writerow(
                                            outdated_record_row)

            else:
                removed_apts += 1
                retired_record_row = []
                for column in outdated_row:
                    retired_record_row.extend(
                                     [outdated_row[column]]
                                     )

                days_posted = get_days_posted(outdated_row["DATE"])

                retired_record_row.insert(3, days_posted)

                retired_record_row.insert(10, datetime.now().date())

                with open(RETIRED_APTS_FILE, 'a', encoding='utf-8')\
                        as retired_apts:
                    retired_apts_writer = csv.writer(retired_apts)
                    retired_apts_writer.writerow(retired_record_row)

                print('\n--  REMOVAL  --')  # Control print
                print(outdated_row["ID"] + " was removed")  # Control print
                print('\n====================\n')  # Control print

    os.remove(outdated_destination_file)


def record_total_variations():
    global already_registered_apts
    global decreased_price_apts
    global increased_price_apts
    global new_apts
    global removed_apts

    current_time = datetime.strptime(
                                     str(datetime.now().time()),
                                     '%H:%M:%S.%f')
    current_time = str(current_time.hour).zfill(2) + ':' +\
        str(current_time.minute).zfill(2) + ':' +\
        str(current_time.second).zfill(2)

    with open(RECORDS_ACCOUNTING_FILE, 'a', encoding='utf-8')\
            as total_variations:
        total_variations_writer = csv.writer(total_variations)
        total_variations_writer.writerow([
                                   datetime.now().date(),
                                   current_time,
                                   new_apts -
                                   decreased_price_apts -
                                   increased_price_apts,
                                   "new apartments"])
        total_variations_writer.writerow([
                                   datetime.now().date(),
                                   current_time,
                                   decreased_price_apts,
                                   "price decrements"])
        total_variations_writer.writerow([
                                   datetime.now().date(),
                                   current_time,
                                   increased_price_apts,
                                   "price increments"])
        total_variations_writer.writerow([
                                   datetime.now().date(),
                                   current_time,
                                   already_registered_apts,
                                   "already registered apartments"])
        total_variations_writer.writerow([
                                   datetime.now().date(),
                                   current_time,
                                   removed_apts,
                                   "removed apartments"])


def get_days_posted(original_date):
    addition_date = datetime.strptime(
                                       original_date,
                                       '%Y-%m-%d'
                                       ).date()
    # If days posted == 0 days
    if str(datetime.now().date() - addition_date) == '0:00:00':
        return '0'
    else:
        return str(
                   datetime.now().date() -
                   addition_date
                    ).split(' ')[0]


def ascii_converter(district):
    ascii_values_replacement = [("À", "a"), ("Á", "a"), ("Ç", "c"),
                                ("È", "e"), ("É", "e"), ("Í", "i"),
                                ("Ï", "i"), ("L·L", "ll"), ("Ò", "o"),
                                ("Ó", "o"), ("Ú", "u"), ("Ü", "u"),
                                ("à", "a"), ("á", "a"), ("ç", "c"),
                                ("è", "e"), ("é", "e"), ("í", "i"),
                                ("ï", "i"), ("l·l", "ll"), ("ò", "o"),
                                ("ó", "o"), ("ú", "u"), ("ü", "u"),
                                ("'", " ")]

    for k, v in ascii_values_replacement:
        district = district.replace(k, v).replace(" ", "-").lower()

    return district


def create_record_file():
    with open(RECORD_FILE, 'w', encoding='utf8')\
      as record_file:
        record_file_writer = csv.writer(record_file)
        record_file_writer.writerow([
                               "DISTRICT",
                               "SUBDISTRICT",
                               "ID",
                               "TITLE",
                               "PRICE (€/month)",
                               "PRICE VARIATION",
                               "SIZE (m²)",
                               "DETAILS",
                               "DATE",
                               "LINK",
                               "SHORT DESCRIPTION"])


def create_price_variations_file():
    with open(PRICE_VARIATIONS_FILE, 'w', encoding='utf-8')\
      as variations_file:
        variations_file_writer = csv.writer(variations_file)
        variations_file_writer.writerow([
                                       "ID",
                                       "DISTRICT",
                                       "SUBDISTRICT",
                                       "DATE",
                                       "PRICE (€/month)",
                                       "LINK"])


def create_retired_apts_file():
    with open(RETIRED_APTS_FILE, 'w', encoding='utf8')\
      as retired_apts:
        retired_apts_writer = csv.writer(retired_apts)
        retired_apts_writer.writerow([
                                "DISTRICT",
                                "SUBDISTRICT",
                                "ID",
                                "DAYS POSTED",
                                "TITLE",
                                "PRICE (€/month)",
                                "PRICE VARIATION",
                                "SIZE (m²)",
                                "DETAILS",
                                "ADDITION DATE",
                                "REMOVAL DATE",
                                "LINK",
                                "SHORT DESCRIPTION"])


def create_total_variations_file():
    with open(RECORDS_ACCOUNTING_FILE, 'w', encoding='utf8')\
      as total_variations:
        total_variations_writer = csv.writer(total_variations)
        total_variations_writer.writerow([
                                       "DATE",
                                       "TIME",
                                       "TOTAL",
                                       "RESULT"])


if __name__ == "__main__":
    last_records_list = []
    price_variations_list = []

    already_registered_apts = 0
    decreased_price_apts = 0
    increased_price_apts = 0
    new_apts = 0
    not_previous_records = False
    removed_apts = 0

    if not os.path.exists(os.path.join(os.getcwd(), RECORD_FILE)):
        not_previous_records = True
        create_record_file()
    if not os.path.exists(os.path.join(
                                       os.getcwd(),
                                       RECORDS_ACCOUNTING_FILE)):
        create_total_variations_file()

    record_new_apts_in_districts_and_subdistricts()

    if not_previous_records is False:
        update_price_variations_file()

    if last_records_list and not_previous_records is False:
        if not os.path.exists(os.path.join(os.getcwd(), RETIRED_APTS_FILE)):
            create_retired_apts_file()
        remove_retired_apts()

    record_total_variations()

    # Control print
    print("\n\nPROCESS ENDED SUCCESSFULLY:")
    print("\t%d - new apartments added"
          % (new_apts - decreased_price_apts - increased_price_apts))
    print("\t%d - price variations detected"
          % (decreased_price_apts + increased_price_apts))
    print("\t\t%d • price decrements detected:"
          % decreased_price_apts)
    print("\t\t%d • price variations detected"
          % increased_price_apts)
    print("\t%d - already registered apartments found"
          % already_registered_apts)
    print("\t%d - removed apartments detected"
          % removed_apts)
