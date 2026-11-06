# ADR-003: The rotor's meshes stay out of git

- Date: 2026-11-06
- Status: accepted 2026-11-06: local repository, no remote, chosen by the person

## Context
The rotor is GeoJolt's "Ugrinsky Style wind Turbine" on MakerWorld. MakerWorld refuses automated
requests (HTTP 403), and downloading needs an account, so it could not be fetched from here. A copy
was already in `~/Downloads`. Its metadata names the title and designer, but holds no MakerWorld model
number, so **matching it to model 861294 rests on the title and the download time**: check it against
the page. Its licence is the "Standard Digital File License": personal use, no redistribution of files.

## Decision
- `cad/vendor/ugrinsky/Ugrinsky_Wind_Turbine.3mf` is gitignored, and its SHA-256 is pinned in
  `src/vawt/io/import_turbine.py`.
- Everything carrying the meshes stays in `build/`, which is also gitignored: extracted STL, render
  STL and the `.FCStd`.
- The renders in `docs/images/` do show the rotor. They are for this project's documentation.

## Consequences
- Anyone else cloning the repository downloads the 3MF themselves. The CAD build then still works.
- **Before publishing the repository or selling a kit, read the licence on the model's page.** A
  private repository of your own is fine; publishing renders or derived parts may not be.
- The booklet (ADR-009) shows the renders too, so it is a private copy for friends until that licence
  has been read.
- The new drive parts are original work and bolt onto the printed rotor; the rotor itself is unchanged
  apart from three drilled holes.
