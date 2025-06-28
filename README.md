# Plandata / Zone Kort
Afsluttende eksamensprojekt som er baseret på data fra Plandatas' WFS(Web Feature Service).

Webapplikationen bruger OpenLayers Streetmap til at vise planer for de forskellige destinatiner i Danmark.
Både som et udtræk af alle planer inden for en bestemt type, men også mere specifikt for adressesøgning.

Det er resultatet af vores scriptarbejde med data og afspejler vores vilje til at visualizere data.

# Skraafoto
Praktik projekt er den del der er baseret på Data Forsyningens Skråfoto tjeneste. 

Bruger OpenLayers Streetmap til at finde skråfotoer ud fra givne koordinater. 
Billederne hentes via API fra Dataforsyningen, samt højdedata fra datafordelingen for at vise nøjagtige billeder. 
Udviklet til Realview som et praktik projekt i 2024. 

## Installation 
> npm install
### For development:
> npm run dev
### For server hosting:
> npm run host

## /Python
> python .\download_from_coordinates.py -f .\coordinates.txt     
### Running tests: 
> pytest -v 

## API Setup
Tokens need to be acquired and inserted into the configuration file at:
skraafoto\src\util\configuration.js

These are the tokens that are needed
### API_STAC_TOKEN  
- from  https://dataforsyningen.dk/                                                   (STAC TOKEN)
### API_DHM_TOKENA  
- from  https://datafordeler.dk/dataoversigt/danmarks-hoejdemodel-dhm/koter/          (DHM API service username)
### API_DHM_TOKENB  
- from  https://datafordeler.dk/dataoversigt/danmarks-hoejdemodel-dhm/koter/          (DHM API service password)

## Virtual Environment
> python -m venv .venv

### Activate the virtual environment on:
#### Windows from root dir
> .venv\Scripts\activate

#### MacOS/Linux from root dir
> source .venv/bin/activate

## To install the dependencies from requirements.txt.

### From root dir
> pip install -r requirements.txt

## Krav til at funktionalitet af points in polygon
> flask --app postgress_connector run -h localhost

Dette er for at få python db connectionen til at virke

### Running on screen 
To view currently running screens:
> screen -ls 

The screen is setup with the name "skraafoto".
To attach to the session it, write:
> screen -r skraafoto

To detach press ctrl + A, then D 
