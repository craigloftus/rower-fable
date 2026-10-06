# Shared anatomical source assets

These are graphical assets from the MakeHuman community repository, released
under CC0. `MAKEHUMAN-LICENSE.md` explains the distinction between the graphical
assets and the application code; `LICENSE.ASSETS.md` contains the asset license.
No MakeHuman application code is copied into this project.

`manifest.json` records the upstream URL and SHA-256 of each source asset.
The builder applies the body targets, reshapes the mesh to rowing proportions,
remaps and blends skin weights, cuts clothing boundaries, and adds authored
hands, footwear, facial colouring and hair. The small mouth-volume targets are
used as pigmentation masks; they are not applied as geometry morphs.

The files called `*-athletic.target` are the upstream average-muscle,
average-weight profile deltas. The rowing proportions are set by `anatomy.py`.
