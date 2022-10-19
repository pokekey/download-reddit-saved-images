from bs4 import BeautifulSoup as bs
import json
import html

"""
Test loading from a site by first downloading the page source
and then experimenting with this script.
"""

FILE_PATH = "redgifs/page source.coffee"

with open(FILE_PATH, "r") as fd:
    content = fd.read()


soup = bs(content)
element = soup.find("script", {"type": "application/ld+json"})
jobj = json.loads(element.text)
video = jobj['video']
contentURL = video['contentUrl']
img_url = html.unescape(contentURL)

print (img_url)

