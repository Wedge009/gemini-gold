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

- **Porting:** the config is converted to the engine's JSON files, and the
  game scripts run under Python 3. Several bugs from earlier conversions are
  fixed: ship stats in `units.json` sat under the wrong names, ships flew
  without shields or reactors, random encounters, cargo missions and
  communications failed to work, and every asteroid field loaded twice.
- **Faithfulness:** the data has been checked against values decoded from the
  original games' files, and brought back into line where Gemini Gold had
  drifted: commodity prices and stock (randomised on every landing, as in the
  original, with Righteous Fire's prices once it begins), equipment sell-back
  prices, upgrade limits, in-system positions (three-dimensional again),
  hidden asteroid fields and jumps, place names, the starting ship, some story
  missions, ship stats and weapons, and Righteous Fire's changes to the
  Kilrathi and its mission ships. Energy, shield recharge, acceleration and
  turn rates are calibrated against play in the original. Privateer and
  Righteous Fire remain one continuous game, as in Gemini Gold.
- **Limited by the engine:** shields, armour and radar can't be upgraded,
  because the engine can't yet remove a fitted item to sell it (a fix is
  offered upstream), and launchers can't be sold. Buying an afterburner
  doesn't fit one, and fitted upgrades take cargo space. Hits on armour don't
  damage ship systems (also offered upstream). Jumps are unlimited, where the
  original allows six per flight, and the story-locked jumps (the Delta chain
  and Valhalla to Eden) are open from the start. Tayla's smuggling
  compartment is missing, lowering shields doesn't save energy, and the old
  engine's Privateer-specific HUD is gone. Ships also pass through each other;
  the cause hasn't been found.
- **On hold:** random encounters, missiles and the size of story-mission
  ambushes differ a lot from the original, and are to be reviewed once combat
  feels right, along with Gemini Gold's own additions.
- **Awaiting research:** repair prices, damaged items' resale value, hull
  trade-in and what each engine level does in the original aren't known yet.

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
