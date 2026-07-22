# wcs-by-year

Body camera violations by year, broken down by violation type — Signal Cleveland.

## Run it

```
python3 build_data.py   # reads the WCS CSV, writes data.json
python3 -m http.server   # then open http://localhost:8000
```

`index.html` loads the chart via `fetch('./data.json')`, so it needs to be served
over HTTP (not opened as a `file://` URL — browsers block local `fetch` of JSON
under that scheme). The input CSV (`Divisional Notice Discipline Cases-Body
Camera Violations.csv`) is committed in this repo; there are no paths outside
this folder.

See the docstring at the top of `build_data.py` for the classification logic
and known gaps (the `safeguard` category undercounts vs. the original
hand-built chart in some years — flagged there for manual review).
