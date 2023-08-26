import shutil
import xml.etree.ElementTree as ET
import os, re

def main():
    addon = ET.parse('metadata.aniscraper/addon.xml').getroot()
    version = addon.attrib['version']

    # Delete old zips
    for file in os.listdir('.'):
        if re.match(r'metadata\.aniscraper-\d+\.\d+\.\d+\.zip', file):
            os.remove(file)
    for file in os.listdir('W:/Archive/Network Share'):
        if re.match(r'metadata\.aniscraper-\d+\.\d+\.\d+\.zip', file):
            os.remove('W:/Archive/Network Share/' + file)

    shutil.make_archive(f'metadata.aniscraper-{version}', 'zip', '.', 'metadata.aniscraper')
    shutil.copy(f'metadata.aniscraper-{version}.zip', 'W:/Archive/Network Share/')

if __name__ == '__main__':
    main()