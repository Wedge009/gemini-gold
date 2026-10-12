# Privateer: Gemini Gold

[Privateer: Gemini Gold](https://sourceforge.net/projects/privateer/) remakes Origin
Systems' *Wing Commander: Privateer* (1993) and its *Righteous Fire* expansion
on the Vega Strike engine. This repository brings Gemini Gold's game data up to
date so it runs on the current
[Vega Strike engine](https://github.com/vegastrike/Vega-Strike-Engine-Source),
which is included as a git sub-module.

## Status

Playable but unfinished. The game builds and runs on Linux: you can trade,
take missions and fight, but it has had only light play-testing, and several
parts of the original game can't yet be reproduced on the current engine.

- **Porting:**
  - The config is converted to the engine's JSON files, and the game scripts
    run under Python 3.
  - Several bugs from earlier conversions are fixed: ship stats in
    `units.json` sat under the wrong names, ships flew without shields or
    reactors, and random encounters, cargo missions and communications failed
    to work.
  - Asteroid fields loaded twice; they now load once, as asteroid fields
    rather than ordinary units.
  - Collision damage is softened, so brushing an asteroid no longer destroys a
    ship outright.
- **Faithfulness:** the data has been checked against values decoded from the
  original games' files, and brought back into line where Gemini Gold had
  drifted:
  - commodity prices and stock (randomised on every landing, as in the
    original, with Righteous Fire's prices once it begins);
  - equipment sell-back prices and upgrade limits;
  - in-system positions (three-dimensional again and at the original's full
    scale, with the autopilot stopping 12 km out);
  - hidden asteroid fields and jumps, and place names;
  - the starting ship, some story missions, and ship stats and weapons;
  - Righteous Fire's changes to the Kilrathi and its mission ships.

  Also:
  - No ship can cloak, as in the original.
  - Energy, shield recharge, acceleration and turn rates are calibrated
    against play in the original.
  - Privateer and Righteous Fire remain one continuous game, as in Gemini
    Gold.
- **Limited by the engine** ("PR submitted" marks a fix offered upstream):
  - Equipment:
    - Shields, armour and radar can't be upgraded, because the engine can't
      yet remove a fitted item to sell it (PR submitted).
    - Launchers can't be sold.
    - A bought afterburner can't be sold after loading a saved game, and
      loading a saved game gives the starting ship a nearly free afterburner
      (PR submitted).
    - Fitted upgrades take cargo space.
  - Damage and repair:
    - Hits on armour don't damage ship systems (PR submitted).
    - The repair bay can't see armour damage, so armour can't be repaired (PR
      submitted).
    - Every hit on a shield lowers that facet's maximum, so shields don't
      recover in fights (PR submitted).
  - Energy:
    - A Centurion's empty capacitor takes about 25 seconds to refill, where
      the original takes about 7.
    - Lowering shields doesn't save energy.
  - Navigation:
    - The autopilot ignores enemies and asteroid fields (PR submitted), and
      flies straight past nav points on its route.
    - Jumps are unlimited, where the original allows six per flight.
    - The story-locked jumps (the Delta chain and Valhalla to Eden) are open
      from the start, as scripts can't yet create a jump point (PR submitted).
  - Other:
    - Tayla's smuggling compartment is missing.
    - The old engine's Privateer-specific HUD is gone.
    - Ships pass through each other, and launched ships sit still for a long
      time before moving erratically; the causes haven't been found.
- **On hold:** random encounters, missiles and the size of story-mission
  ambushes differ a lot from the original. They're to be reviewed once combat
  feels right, along with Gemini Gold's own additions.
- **Awaiting research:** these aren't known yet for the original:
  - repair prices;
  - damaged items' resale value;
  - hull trade-in;
  - what each engine level does;
  - whether a destroyed component can be repaired or must be bought again.

The work that data and scripts alone can do is largely finished. Most of what
remains needs changes to the Vega Strike engine, so further progress depends
mainly on that.

[PORTING.md](PORTING.md) lists every change, the engine work it waits on, and
every remaining difference from the original games.

## Running the game

The engine's `script/bootstrap` installs its build dependencies on supported
Linux distributions. It needs SDL3, so older releases (such as Ubuntu 24.04)
won't build it without SDL3 from elsewhere.

    git clone --recurse-submodules https://github.com/Wedge009/gemini-gold
    cd gemini-gold/engine
    sudo script/bootstrap
    script/build --preset-name=linux-ninja-pie-enabled-glvnd-release
    cd ..
    ./run.sh

Settings, saved games and logs go in `~/.gemini-gold`. See
[PORTING.md](PORTING.md#setting-up) for using another engine build.

## History

Gemini Gold was developed on SourceForge, reaching version 1.03 in 2009.
[DMJC/Privateer_Gold](https://github.com/DMJC/Privateer_Gold) imported its data
in 2022 and began the move to the modern engine and Python 3. This repository
is a fork of that work.

## Licences

*Wing Commander: Privateer*'s design and content are by Origin Systems.
Gemini Gold's art (images, sound, music and animation) may be used only within
the Gemini Gold project, with credit to the artists and the project, and never
for profit; see [art-license.txt](art-license.txt). The code is under the GNU
General Public License, version 2 ([vega-license.txt](vega-license.txt)).
