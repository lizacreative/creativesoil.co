# Test3 Static Review Build

This folder contains the current **test3** review site as a self-contained static build. It is committed on the `test3-static-review` branch only and does not modify the production branch.

## Contents

| Path | Purpose |
|---|---|
| `site/` | The complete static site currently deployed to the isolated test3 review deployment. |
| `tools/repair_static_export.py` | The reproducible static-export repair script used to create the review build. |

Open `site/index.html` in a static server to inspect the build locally. The `site/` directory contains all routes, images, fonts, and browser-side behavior required by the current test3 version.

> This branch is for review and editing of the test3 static implementation. Changes do not affect production unless they are deliberately merged into another branch and deployed.

The contact page uses the source page's native form markup, with the header and footer changes applied after the page has initialized to preserve the existing form behavior.
