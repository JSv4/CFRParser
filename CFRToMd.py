import xml.etree.ElementTree as ET
from typing import Optional


def process_cfr_xml_element(element) -> str:
    """
    Process an XML element and return its corresponding Markdown representation.

    :param element: An XML element from the CFR XML data
    :type element: xml.etree.ElementTree.Element
    :return: The Markdown representation of the input XML element
    :rtype: str
    """

    title = element.HEAD.string if element.HEAD else "NO TITLE"
    paragraphs = []
    for p in element.find_all("P"):
        if p.string:
            paragraphs.append(p.string)
        else:
            paragraphs.append("\n")
    text = "\n".join(paragraphs)
    citation = element.CITA.string if element.CITA else "NO CITE"

    return f"""
    # {title}
    
    {text}
    
    **{citation}**
    """
