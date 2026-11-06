# Skråfoto & Plandata

A web app for exploring Danish **oblique aerial photos** (skråfotos) and **planning zones** on a map, live at **[skraafoto.machinemal.eu](https://skraafoto.machinemal.eu)**.

It started as a final exam project (planning data) and an internship project (oblique photos) and has been developed further since.

## Features

- **Oblique photo viewer:** search an address and see aerial photos of it from five directions (north, south, east, west and straight down), with the point marked using terrain elevation
- **Multi-viewer:** compare several photo directions side by side
- **Zone map:** municipal and local plans (kommuneplaner and lokalplaner) shown on an OpenLayers map, by layer or by address

## Data sources

- [Dataforsyningen](https://dataforsyningen.dk/): the skråfoto STAC API, address search (gsearch) and address points
- [Datafordeler](https://datafordeler.dk/): Danmarks Højdemodel (DHM) terrain elevation
- Planning data from Plandata.dk, prepared with the scripts in [Plandata](https://github.com/AlexanderStubMichelsen/Plandata) and shipped as a GeoPackage (`plandata.gpkg`, stored with Git LFS)

## Tech

React 18 + Vite + OpenLayers ([SAUL](https://www.npmjs.com/package/@dataforsyningen/saul) for skråfoto data) on the frontend; **Flask** + GeoPandas on the backend.

**API keys never reach the browser.** The Flask backend proxies all Dataforsyningen and Datafordeler calls under `/api/proxy/*` and adds the credentials server-side, including for the photo files themselves.

## Run locally

Requires Node 20 and Python 3.12+.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.flask.example .env.flask                    # then fill in the three values below
npm install
npm run dev                                         # Flask on :5000 and Vite on :5173
```

`.env.flask`:

| Variable | Where to get it |
|---|---|
| `DATAFORSYNINGEN_TOKEN` | A token from [dataforsyningen.dk](https://dataforsyningen.dk/) |
| `DHM_USERNAME`, `DHM_PASSWORD` | A service user (tjenestebruger) on [datafordeler.dk](https://datafordeler.dk/) with access to DHM |

Python tests: `pytest -v` (in `python/`).

## Deployment

The `server` branch deploys automatically ([deploy-server.yml](.github/workflows/deploy-server.yml)): build the frontend, copy it together with the Flask app and GeoPackage to the server, write the credentials from repository secrets, install the Python dependencies ([requirements-server.txt](requirements-server.txt)) and restart the service behind gunicorn.

## Python tools

`python/download_from_coordinates.py` downloads skråfotos for a list of coordinates:

```bash
python python/download_from_coordinates.py -f python/coordinates.txt
```
