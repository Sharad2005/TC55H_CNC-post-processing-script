# Release checklist

## Release identity

- Version: `v1.0.0`
- Title: `TC55H Fusion 360 and FreeCAD CAM post processors v1.0.0`
- Target branch: `main`
- Controller contract: TC55H Baseline 1.0

## Before publishing

- [x] Fusion post executed on the target TC55H V4.005 machine.
- [x] FreeCAD adapter generated a real CAM Job output file.
- [x] FreeCAD output passed the standalone format validator.
- [x] FreeCAD and Fusion controller-language structures were compared.
- [x] Python and JavaScript regression suites passed.
- [x] Release file checksums were verified.
- [x] Documentation distinguishes format, software, and physical-machine evidence.
- [ ] Decide the public license or document confirmed redistribution terms for the Autodesk-derived Fusion post.
- [ ] Push `main` and the `v1.0.0` tag.
- [ ] Create the GitHub release using `docs/RELEASE_NOTES_v1.0.0.md`.

## Final verification commands

```sh
node tests/test_tc55h_cps.js
python3 -m unittest discover -s tests -p 'test_*.py'
shasum -a 256 -c SHA256SUMS
git status --short
```

The final command should print nothing. Do not attach generated production `P*.TXT` files, third-party manuals, machine parameters, credentials, or local FreeCAD/Fusion configuration files to the release.

## Publishing commands

```sh
git push origin main
git push origin v1.0.0
```

On GitHub, create a release from tag `v1.0.0`, paste the release notes, and do not mark it as a prerelease. Keep the FreeCAD status described as software-validated and format-compatible, not physically machine-tested.
