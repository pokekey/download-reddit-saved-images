#
# Read html links from a file and download each to a file.
# The links are assumed to be in the format:
#   http://www.example.com/file.txt
#   http://www.example.com/file2.txt
import typing as t
import requests
import pathlib
import csv

names: t.Dict[str,str] = {
    "ak": "anastasiyakvitko",
    "al": "alinalewis",
    "as": "anogsuriyakul",
    "ba": "bethanylilyapril",
    "bc": "blossomandbuttercups",
    "bt": "bunnyteethbabe",
    "cc": "casandracass",
    "cr": "cecerosee",
    "cz": "chairamazzola",
    "dy": "danielleyayalaa",
    "ed": "emilyducati",
    "em": "eviewolfemodel",
    "eo": "elizabethoceans",
    "fa": "itsflexyamy",
    "fbb": "fullerbustbestie",
    "ff": "lafemmefantome",
    "gg": "giagenevieve",
    "hrs": "heinzrichardschneider",
    "jc": "jennachew",
    "jm": "juliaticamilf",
    "kk": "katya.b.karlova",
    "lb": "leboudoirdebianca",
    "levi": "levicoralynn",
    "lk": "louisakhovanski",
    "ma": "melynaaelyssxenia",
    "mm": "marietheresaandlumieres",
    "mo": "miladamoore",
    "ms": "magdalinasoltan",
    "pr": "pureruby",
    "ps": "prinsessemart",
    "rj": "rachelannjensen",
    "se": "sophiexellodie",
    "sk": "sklanaaa",
    "sm": "solomiamaievska",
    "sn": "sadisticnitemare",
    "sss": "silkyshinysoft",
    "sv": "streetview",
    "tlc": "tightlacedchaos",
    "tv": "threnodyinvelvet",
    "vc": "valkyriecorsets",
    "vm": "vismaramartina",
    "zs": "ziennasonne",
    "zv": "zoevolf",
}

extensions: t.Dict[str,str] = {
    "m": "mp4",
    "j": "jpg",
}

def download_file(url, filename: pathlib.Path):
    '''use requests to download a file'''
    # create the file if it doesn't exist
    filename.touch(exist_ok=True)
    # open the file in binary mode
    with open(filename, 'wb') as f:
        # get request
        r = requests.get(url)
        # write to file
        f.write(r.content)


def simple(linkfilename: str, download_name_base: str, start_index: int):
    """Download files from a list of urls."""

    # Open the file with read only permit
    with open(linkfilename, "r") as f:
        links = f.readlines()

    i: int = start_index
    for link in links:
        # Remove whitespace characters like `\n` at the end of each line
        link = link.strip()
        # create a file name with a number
        download_file_name = f"{download_name_base}_{i:04d}.mp4"
        i += 1
        print ("Downloading file: %s" % download_file_name)
        download_file(link, pathlib.Path(download_file_name))


def fancy(linkfilename: str, namemap: t.Dict[str,str], target_dir: str):
    """Download files from a list of urls."""

    # Open the file with read only permit
    # person,description,ext,url
    links: list[dict[str,str]] = []
    with open(linkfilename, "r", newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            links.append(row)

    for link in links:
        person = namemap.get(link['person'], link['person'])
        if link['ext'] == '':
            link['ext'] = 'j'
        extention = extensions.get(link['ext'], link['ext'])

        description = link['description'].replace(' ', '_')

        # Remove whitespace characters like `\n` at the end of each line
        url = link['url'].strip()
        # create a file name with a number
        download_file_name = f"{person}_{description}.{extention}"
        download_path = pathlib.Path(target_dir, download_file_name)
        
        print ("Downloading file: %s" % download_file_name)
        download_file(url, download_path)

#main("video_link_list.txt", "softwparkling", 1)

fancy("videolist.csv", names, "sv")