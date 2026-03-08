# Voxel Skyways (Desktop Edition)

This project was rewritten from a browser prototype into a standalone desktop game using **pygame** for smoother input/render behavior and fewer browser-related glitches.

## Run

```bash
python3 -m pip install pygame
python3 game.py
```

## Controls

- `Enter`: start flight
- `W/A/S/D`: move
- `Space`: ascend
- `Left Ctrl` / `Right Ctrl`: descend
- `Mouse`: look around
- `Esc`: open/close options menu

## Options menu controls (while menu is open)

- `Left/Right`: render distance
- `Up/Down`: flight speed
- `1/2`: time of day
- `3/4`: fog
- `-` / `=`: saucer count
- `C`: toggle clouds

## Dev smoke check

```bash
python3 game.py --headless --max-frames 5
```
