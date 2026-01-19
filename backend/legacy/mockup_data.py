import json
from pathlib import Path


class Tile:
    def __init__(self, title, text, meta_information=dict(), link_from_tiles=list(), pop_out=dict(), column=0, row=0, deletable=True):
        self.title = title
        self.text = text
        self.meta_information = meta_information
        self.link_from_tiles = link_from_tiles
        self.pop_out = pop_out
        self.column = column
        self.row = row
        self.deletable = deletable
        self.status = 'active'  # set to inactive if should be deleted after hand-off to backend

class PopOut:
    # Different Popout Structures to delete, edit, etc? Is that necessary?
    pass


based_on =  [{
                "Name": "Quelle1",
                "exakte URL": "https://example.com",
                "direktes Zitat": "Zitat 1",
                "abgerufen am": "2025-01-01"
            },
            {
                "Name": "Quelle2",
                "exakte URL": "https://example.org",
                "direktes Zitat": "Zitat 2",
                "abgerufen am": "2025-01-02"
            }]

law_tile = Tile(
    'Gesetzesentwurf A',
    'Gesetzesentwurf A ist ein Entwurf um xyz zu machen',
    {'based_on': based_on, 'long form of the law': 'Das Gesetz ist dazu da um...'},
    column=0,
    row=0,
    deletable=False
)
law_tile.id = "law_tile"

prerequisite_1 = Tile(
    'Vorgabe 1',
    'Auf jeden Fall Homeoffice-Bedingungen prüfen',
    {'Hinweis': 'Beispielhafte Meta-Informationen zur Vorgabe 1.'},
    link_from_tiles=[law_tile],
    column=1,
    row=0,
    deletable=True
)
prerequisite_1.id = "prerequisite_1"

prerequisite_2 = Tile(
    'Vorgabe 2',
    'Auf jeden Fall Strecke zur Arbeit prüfen.',
    link_from_tiles=[law_tile],
    column=1,
    row=1,
    deletable=True
)
prerequisite_2.id = "prerequisite_2"

prerequisites_list = [prerequisite_1, prerequisite_2]

process_1 = Tile(
    'Prozess 1',
    'HO und Fahrweg prüfen',
    {'Hinweis': 'Demo-Prozess: hängt von beiden Vorgaben ab.'},
    link_from_tiles=[prerequisite_1, prerequisite_2],
    column=2,
    row=0,
    deletable=True
)
process_1.id = "process_1"

processes_list = [process_1]

prerequisites_button = 'generate prerequisites from law'
processes_button = 'generate processes from prerequisites'


def as_json_dict():
    def serialise(tile):
        return {
            "id": getattr(tile, "id", tile.title),
            "title": tile.title,
            "text": tile.text,
            "meta_information": tile.meta_information,
            "link_from_tile": [getattr(t, "id", t.title) for t in (tile.link_from_tiles or [])] if tile.link_from_tiles else [],
            "column": getattr(tile, "column", 0),
            "row": getattr(tile, "row", 0),
            "deletable": getattr(tile, "deletable", True),
        }

    tiles = [
        law_tile,
        *prerequisites_list,
        *processes_list
    ]

    return {
        "tiles": [serialise(t) for t in tiles],
        "column_buttons": [
            {"id": "prereq", "label": prerequisites_button, "tiles": [t.id for t in prerequisites_list]},
            {"id": "processes", "label": processes_button, "tiles": [t.id for t in processes_list]},
        ],
        "initial_visible": ["law_tile"],
    }


def write_json(path=None):
    output_path = Path(path) if path else Path(__file__).with_name("mockup_data.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(as_json_dict(), f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    write_json()
