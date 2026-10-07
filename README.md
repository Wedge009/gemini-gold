# Privateer: Gemini Gold

[Privateer: Gemini Gold](https://sourceforge.net/projects/privateer/) remakes Origin
Systems' *Wing Commander: Privateer* (1993) and its *Righteous Fire* expansion
on the Vega Strike engine. This repository brings Gemini Gold's game data up to
date so it runs on the current
[Vega Strike engine](https://github.com/vegastrike/Vega-Strike-Engine-Source),
which is included as a git sub-module.

## Status

Work in progress. The game builds and runs on Linux, but it hasn't had much
play-testing yet.

- **Porting:** the config is converted to the engine's JSON files, and the
  game scripts run under Python 3. Several bugs from earlier conversions are
  fixed: ship stats in `units.json` sat under the wrong names, ships flew
  without shields or reactors, random encounters and cargo missions failed to
  run, and every asteroid field loaded twice.
- **Faithfulness:** the data is being checked against values decoded from the
  original games' files, and brought back into line where Gemini Gold had
  drifted. So far this covers commodity prices and stock (randomised on every
  landing, as in the original, with Righteous Fire's prices once it begins),
  equipment sell-back prices, upgrade limits, in-system positions (now
  three-dimensional again), hidden asteroid fields and jumps, place names, the
  starting ship, some story missions, ship stats and weapons, and Righteous
  Fire's changes to the Kilrathi and its mission ships. Privateer and
  Righteous Fire remain one continuous game, as in Gemini Gold.
- **Still to come:** random encounters and missiles differ a lot from the
  original and are to be reviewed. Some fixes wait on changes offered to the
  Vega Strike engine, among them selling upgrades and the story-locked jumps.

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
