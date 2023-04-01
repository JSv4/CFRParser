import json
from pathlib import Path

import requests as requests
from enum import Enum
from typing import Union
from urllib.parse import quote

from bs4 import BeautifulSoup

from CFRToMd import process_cfr_xml_element


class DateChoice(Enum):
    LATEST_ISSUE_DATE = "latest_issue_date"
    LATEST_AMENDED_ON = "latest_amended_on"


def get_ecfr_link_to_appendix(
        title_num,
        subtitle_num,
        chapter_num,
        part_num,
        subpart_num,
        appendix_num,
) -> str:
    """
    Returns a link to the eCFR viewer for the specified appendix.

    :param title_num: The title number of the CFR (e.g. 29 for Labor).
    :param subtitle_num: The subtitle number of the CFR.
    :param chapter_num: The chapter number of the CFR.
    :param part_num: The part number of the CFR.
    :param subpart_num: The subpart number of the CFR containing the appendix.
    :param appendix_num: The number of the appendix.
    :return: A link to the eCFR viewer for the specified appendix.
    """
    return f"https://www.ecfr.gov/current/title-{title_num}/subtitle-" \
           f"{subtitle_num}/chapter-{chapter_num}/part-{part_num}/subpart-{subpart_num}/appendix-{quote(appendix_num)}"

def get_ecfr_link_to_section(
        title_num,
        subtitle_num,
        chapter_num,
        part_num,
        subpart_num,
        section_num,
) -> str:
    """
    Returns a link to the eCFR viewer for the specified section.

    :param title_num: The title number of the CFR (e.g. 29 for Labor).
    :param subtitle_num: The subtitle number of the CFR.
    :param chapter_num: The chapter number of the CFR.
    :param part_num: The part number of the CFR.
    :param subpart_num: The subpart number of the CFR containing the section.
    :param section_num: The number of the section.
    :return: A link to the eCFR viewer for the specified section.
    """
    return f"https://www.ecfr.gov/current/title-{title_num}/subtitle-" \
           f"{subtitle_num}/chapter-{chapter_num}/part-{part_num}/subpart-{subpart_num}/section-{quote(section_num)}"


def get_title_date(title_number: int, date_choice: DateChoice) -> Union[str, None]:
    """
    Get the latest issue date or latest amended on date for a given title number.

    Args:
        title_number (int): The title number to get the date for.
        date_choice (DateChoice): An enumeration representing the desired date type:
                                  latest_issue_date or latest_amended_on.

    Returns:
        str: The date in the format "YYYY-MM-DD" if the title number is found,
             otherwise returns None.
    """
    response = requests.get("https://www.ecfr.gov/api/versioner/v1/titles")
    response.raise_for_status()
    titles = response.json()["titles"]

    for title in titles:
        if title["number"] == title_number:
            return title[date_choice.value]

    return None


def get_cfr_title_xml(title):
    base_url = "https://www.ecfr.gov/api/versioner/v1/full/"
    endpoint = f"{get_title_date(title, DateChoice.LATEST_ISSUE_DATE)}/title-{title}.xml"
    url = base_url + endpoint
    print(f"Request file from {url}")
    headers = {"accept": "application/xml"}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.text
    else:
        print(f"Request failed with status code: {response.status_code}")
        return None


def fetch_and_parse_cfr_xml(title_num):
    # create a Path object for the file you want to check
    file_path = Path(f'./cache/title{title_num}.xml')

    # check if the file exists
    if file_path.is_file():
        print("File in cache")
        xml_data = file_path.open().read().encode("utf-8")
    else:
        print("File not in cache. Retrieve.")
        # Make sure the director exists
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True)

        xml_data = get_cfr_title_xml(title_num)
        file_path.write_text(xml_data)

    print(f"XML loaded for title {title_num}")

    root = BeautifulSoup(xml_data, features="xml")

    title = root.find("DIV1")
    title_description = title.HEAD.string if title.HEAD else ""
    print(f"Title description: {title_description}")

    parsed_sections = []

    # Chapter is Div3
    # subchapter is Div4

    for subtitle in root.find_all("DIV2"):
        subtitle_number = subtitle['N']
        subtitle_description = subtitle.HEAD.string if subtitle.HEAD else ""
        print(f"Subtitle {subtitle_number} - {subtitle_description}")

        for chapter in subtitle.find_all("DIV3"):
            chapt_number = chapter["N"]
            chapt_description = chapter.HEAD.string if chapter.HEAD else ""

            print(f"Subchapter {chapt_number} - {chapt_description}")

            for subchapter in chapter.find_all("DIV4"):
                subchapter_number = subchapter['N']
                subchapter_description = subchapter.HEAD.string if subchapter.HEAD else ""
                print(f"Subchapter {subchapter_number} - {subchapter_description}")

                for part in root.find_all("DIV5"):
                    part_number = part["N"]
                    part_description = part.HEAD.string if part.HEAD else ""
                    print(f"Part {part_number} - {part_description}")

                    for sub_part in root.find_all("DIV6"):
                        sub_part_number = sub_part["N"]
                        sub_part_description = sub_part.HEAD.string if sub_part.HEAD else ""
                        print(f"Sub part {sub_part_number}: {sub_part_description}")

                        for section in sub_part.find_all("DIV8"):
                            section_number = section["N"]
                            section_description = section.HEAD.string if section.HEAD else ""

                            ecfr_link = get_ecfr_link_to_section(
                                    title_num,
                                    subtitle_number,
                                    chapt_number,
                                    part_number,
                                    sub_part_number,
                                    section_number
                                )
                            metadata = {
                                "title_number": title_num,
                                "title_description": title_description,
                                "chapter_number": chapt_number,
                                "chapter_description": chapt_description,
                                "subchapter_number": subchapter_number,
                                "subchapter_description": subchapter_description,
                                "part_number": part_number,
                                "part_description": part_description,
                                "sub_part_number": sub_part_number,
                                "sub_part_description": sub_part_description,
                                "section_number": section_number,
                                "section_description": section_description,
                                "url": ecfr_link
                            }

                            result = {
                                "page_content": process_cfr_xml_element(section) + f"\n\n__{ecfr_link}__",
                                "metadata": metadata
                            }

                            section_file = Path(f"./documents/title_{title_num}/subtitle_{subtitle_number}/chap_"
                                                f"{chapt_number}/subchapt_{subchapter_number}/part_{part_number}/"
                                                f"subpart_{sub_part_number}/{quote(section_number)}.json")

                            if not section_file.parent.exists():
                                section_file.parent.mkdir(parents=True)

                            section_file.write_text(json.dumps(result, indent=4))

                        for appendix in sub_part.find_all("DIV9"):
                            appendix_number = appendix['N']
                            appendix_description = appendix.HEAD.string if appendix.HEAD else ""

                            ecfr_link=get_ecfr_link_to_appendix(
                                    title_num,
                                    subtitle_number,
                                    chapt_number,
                                    part_number,
                                    sub_part_number,
                                appendix_number
                                )
                            metadata = {
                                "title_number": title_num,
                                "title_description": title_description,
                                "chapter_number": chapt_number,
                                "chapter_description": chapt_description,
                                "subchapter_number": subchapter_number,
                                "subchapter_description": subchapter_description,
                                "part_number": part_number,
                                "part_description": part_description,
                                "sub_part_number": sub_part_number,
                                "sub_part_description": sub_part_description,
                                "appendix_number": appendix_number,
                                "appendix_description": appendix_description,
                                "url": ecfr_link
                            }

                            result = {
                                "page_content": process_cfr_xml_element(appendix) + f"\n\n__{ecfr_link}__",
                                "metadata": metadata
                            }

                            appendix_file = Path(f"./documents/title_{title_num}/subtitle_{subtitle_number}/chap_"
                                                f"{chapt_number}/subchapt_{subchapter_number}/part_{part_number}/"
                                                f"subpart_{sub_part_number}/{quote(appendix_number)}.json")

                            if not appendix_file.parent.exists():
                                appendix_file.parent.mkdir(parents=True)

                            appendix_file.write_text(json.dumps(result, indent=4))
