import shutil
import xml.etree.ElementTree as ET
import os, re

def clear(name):
    for file in os.listdir('.'):
        if re.match(rf'{name}-\d+\.\d+\.\d+\.zip', file):
            os.remove(file)
    for file in os.listdir('W:/Archive/Network Share'):
        if re.match(rf'{name}-\d+\.\d+\.\d+\.zip', file):
            os.remove('W:/Archive/Network Share/' + file)

def build(name):
    addon = ET.parse(f'{name}/addon.xml').getroot()
    version = addon.attrib['version']

    # Delete old zips
    clear(name)

    if not os.path.exists('dest'):
        os.makedirs('dest')
    
    shutil.make_archive(f'dest/{name}-{version}', 'zip', '.', name)
    shutil.copy(f'dest/{name}-{version}.zip', 'W:/Archive/Network Share/')

def main():
    build("metadata.aniscraper")

if __name__ == '__main__':
    main()