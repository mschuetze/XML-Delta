# XML-Delta
Script to compare two XML files and create a new file that only contains new data (delta)

## Voraussetzungen
### 1. Python 3
- überprüfen, ob Python 3 bereits installiert ist:
  - folgenden Code kopieren: `python3 --version`
  - App TERMINAL öffnen
  - Code einfügen und mit ENTER bestätigen
  - wenn Ausgabe **"Python 3.x.y"** (oder höher):
    - weiter zu Punkt 2.
  - andernfalls:
    - Python 3 von hier herunterladen und installieren: https://www.python.org/downloads/macos/

### 2. lxml
- lxml installieren
  - folgenden Code kopieren: `pip3 install lxml`
  - App TERMINAL öffnen
  - Code einfügen und mit ENTER bestätigen

## Installation
Zunächst sicherstellen, dass die beiden Voraussetzungen erfüllt sind (siehe oben).
- Neueste Version des Tools herunterladen: https://github.com/mschuetze/XML-Delta/releases
  - das ZIP findet sich in der unteren Hälfte des Kastens, bezeichnet als **Source code (zip)**
- ZIP entpacken und im Ordner deiner Wahl ablegen (z.B. Schreibtisch)

## Benutzung
ACHTUNG: Für die Nutzung des Skripts benötigen wir sowohl das aktuelle XML, als auch das "alte".
- aktuelles XML, welches die Änderungen / Ergänzungen enthält, hier herunterladen: https://conferences-preview.s3-website-eu-west-1.amazonaws.com/#/conferences
- mittels **conferenceTransform** die 4 XML-Dateien für den Workflow erstellen
- altes + neues XML in Ordner **INPUT** kopieren (jeweils einzeln für die 4 Dateien)
- Datei **run_xml_delta.applescript** doppelklicken und in Skripteditor ausführen (Play-Button, oben rechts)
  ![Skripteditor](image01.png)
- neues XML wird in Ordner **OUTPUT** generiert
- diese XML-Datei in den Projektordner verschieben / kopieren