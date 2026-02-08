# sc2kne patcher

This collection of Python3 scripts enable a user to bootstrap a working version of Simcity 2000: Network Edition on a modern day Windows install.

## Background

As a major fan of this city simulator, I noticed the only way to enable a modern installation was to run binaries posted on Reddit/game knowledge sites that may be dead or have little to no documentation. As a challenge, I opted to create a modern, open source version of these binaries that achieve feature parity with their intended use. 

The most relevant, up-to-date resource with documentation is located here:

[ankarstrom.se/](https://ankarstrom.se/~john/etc/2knet/)

## Status

There are two major patches that have been released to get this working on modern hardware:

- Interoperability patch ✅
- 2019 Patch made by `click4dylan` ⌛


I have opted to create an installer similar to the Interoperability patch to ease the install a bit. You are free to get your own files. This may break the script though, so if that happens, please open an issue and I will address it via reproduction and mitigation.

The 2019 `click4dylan` will be implemented manually, as some users may not like the game mechanic changes. I plan to incorporate quality of life changes prior to game mechanic changes after analysis of this patch.

## Instructions

1. Clone the repo
2. Run the following:

```
pip install -r requirements.txt
python src/main.py
```
3. Follow the prompts
4. Enjoy your game

## Future plans

The future is something that people always talk about which never happens. This is phase 1 of a 3 phase project. The phases are:

1. Feature parity open source patches
2. Making a fully open source server, replacing `2KSERVER.exe`
3. Making a high resolution GUI, replacing `2KCLIENT.exe`

Once this is complete, we can extend the game logic and the game client and build from here.

## Differences from other projects

There are a few projects that are similar to this. Some that come to mind are:

- [OpenSC2K](https://github.com/nicholas-ochoa/OpenSC2K)
- [isometric-city](https://github.com/amilich/isometric-city)

These are amazing projects and I highly suggest looking at them. Despite these, I wanted to create this project to do the following:

1. Make this legacy code work on modern systems
2. Reuse game assets
3. Enhance the logic
4. Practice reverse engineering

Either way, for city builders, for me, this is the golden standard.

Enjoy!