# Script to convert XML to JSON

import xml.etree.ElementTree as ET
import xmltodict
import json

tree = ET.parse('filename.xml')
root = tree.getroot()

d = root.findall('tag_you_want') # Get a particular tag you want from the XML (optional)

for m in d:
    for node in m:
        s = node.text # Getting that tags XML string

j = xmltodict.parse(s)

with open('json_of_filename.json', 'w+') as f:
    f.write(json.dumps(j, indent=4))
