# Azur Lane RPG

Embark on an adventure with our beloved Shipgirls. Protect the seas and drive back the invading Siren threat!

Begin your journey as a fresh-faced Commander at your faction’s port. Build your fleet over time by researching and constructing new Shipgirls in the shipyard, then craft weapons and equipment in the gear lab to strengthen their capabilities. Conduct sorties, take on increasingly dangerous enemies, and venture deeper into Siren-controlled territory. Between battles, purchase furniture and decorate your port, creating a place your Shipgirls can call home.

## Instructions

### Web and Windows Versions

To play this game on the web or download the windows version, visit the [itch.io page](https://manguino.itch.io/azur-lane-rpg).

### On Other Platforms

To play on other platforms, you must run the game manually.

1. Follow the [Python installation instructions](https://www.python.org/downloads/) to install Python on your device.
2. Clone the release branch of this repo:
```bash
git clone -b "release-1.0" --single-branch "https://github.com/HuMangoPP/azur_lane_rpg.git"
```
3. (Recommended) Create a virtual environment:
```bash
python -m venv env
```
4. Install dependencies:
```bash
pip install -r requirements/prod.txt
```
5. Run the game:
```bash
python3 main.py
```

## Notes

* If you have just constructed a new shipgirl or are entering a new encounter, the game will need to load new live2d assets, which can some time. The game is (probably) not frozen and is unlikely to crash.

* If you encounter any bugs, feel free to raise an issue or leave a comment.