"""Generate Anki flashcards for British Prime Ministers using WikiData.
James Brind, October 2021"""

import sys
import os
import genanki
from SPARQLWrapper import SPARQLWrapper, JSON

# Set constants
ENDPOINT_URL = "https://query.wikidata.org/sparql"  # Where to fetch data
QUERY_FILE = "query.sparql"  # Path to a query file
USER_AGENT = "wikidata2anki Python/%s.%s" % (  # Identify ourselves to WikiData
    sys.version_info[0],
    sys.version_info[1],
)
IMGDIR = "./img"  # Relative path to store images

# Load query
with open(QUERY_FILE, "r") as f:
    query_str = f.read()

# Send to remote and get results
# After the WikiData Query Service example script.
sparql = SPARQLWrapper(ENDPOINT_URL, agent=USER_AGENT)
sparql.setQuery(query_str)
sparql.setReturnFormat(JSON)
results = sparql.query().convert()

# Throw away metadata and just keep values
results = results["results"]["bindings"]
results = [{ki: ri[ki]["value"] for ki in ri} for ri in results]

# Now loop over results and manipulate the data as required
for ri in results:

    # Join start and end dates into a year range field
    year_st = int(ri["start"][:4])
    try:
        year_en = int(ri["end"][:4])
        if year_st == year_en:
            ri["years"] = "%d" % year_st
        else:
            ri["years"] = "%d-%d" % (year_st, year_en)
    except KeyError:
        ri["years"] = "%d-" % year_st

    # Generate image filename based on the PM's name
    imgname = (
        ri["personLabel"].replace(" ", "").split(",")[0]
        + "."
        + ri["pic"].split(".")[-1]
    )

    # Store image and HTML snippet
    ri["imgpath"] = os.path.join(IMGDIR, imgname)
    ri["imghtml"] = r'<img src="%s">' % imgname

    # Only download and resize if we have not got the image already
    if not os.path.exists(ri["imgpath"]):
        os.system("wget -nv -O %s %s" % (ri["imgpath"], ri["pic"]))
        os.system("convert -resize 360 %s %s" % (ri["imgpath"], ri["imgpath"]))

    # Fill in blank predecessor/successors
    for lab in ["sucLabel", "preLabel"]:
        try:
            ri[lab]
        except KeyError:
            ri[lab] = "N/A"

# For multiple-term PMs, note as such
for ri in results:
    others = [
        rj for rj in results if rj["personLabel"] == ri["personLabel"] and not ri == rj
    ]
    if len(others) > 0:
        ri["others"] = "Also PM: " + ", ".join([rj["years"] for rj in others])
    else:
        ri["others"] = ""

# Hardcode randomly-generated identifiers
MODEL_ID = 1246910694
DECK_ID = 1590691877

# Data for PM cards
my_model = genanki.Model(
    MODEL_ID,
    "British PM",
    fields=[
        {"name": "PM"},
        {"name": "Party"},
        {"name": "Years"},
        {"name": "Picture"},
        {"name": "PartyColour"},
        {"name": "Predecessor"},
        {"name": "Successor"},
        {"name": "Other"},
    ],
    sort_field_index=2,  # Sort by years in office
    templates=[
        {
            "name": "PM from Years",
            "qfmt": """
                {{Years}}
                <br>
                <p id="pcol" style="border-bottom: 10px solid #{{PartyColour}};">
                {{Party}}
                </p>
                <p>
                Preceeded by:<br>
                {{Predecessor}}<br><br>
                Succeeded by:<br>
                {{Successor}}
                </p>""",
            "afmt": """
                {{FrontSide}}<br>
                <hr id="answer">
                <p>{{PM}}</p>
                <p>{{Picture}}</p>""",
        },
        {
            "name": "Years from PM",
            "qfmt": """
                {{PM}}
                <p>
                Preceeded by:<br>
                {{Predecessor}}<br><br>
                Succeeded by:<br>
                {{Successor}}
                </p>
                {{Picture}}""",
            "afmt": """
                {{FrontSide}}<br>
                <hr id="answer">
                {{Years}}<br>
                <p id="pcol" style="border-bottom: 10px solid #{{PartyColour}};">
                {{Party}}
                </p>
                <p>
                {{Other}}
                </p>""",
        },
    ],
    css="""
    .card {
        font-size: 20px;
        text-align: center;
        }
    #pcol {
        margin: auto;
        width: 340px;
        padding:10px;
        }
    #answer {
        margin-top: 10px;
        }""",
)

# Initialise deck
my_deck = genanki.Deck(DECK_ID, "British Prime Ministers")

# Loop over results

field_names = [
    "personLabel",
    "party",
    "years",
    "imghtml",
    "partycol",
    "preLabel",
    "sucLabel",
    "others",
]
for ri in results:
    my_deck.add_note(
        genanki.Note(model=my_model, fields=[ri[ki] for ki in field_names])
    )

my_package = genanki.Package(my_deck)
my_package.media_files = [ri["imgpath"] for ri in results]
my_package.write_to_file("output.apkg")
