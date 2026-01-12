-- v0.3.1
#!/usr/bin/env osascript

set scriptPath to POSIX path of (path to me)
set scriptDirectory to do shell script "dirname '" & scriptPath & "'"

-- Nutze die stabile xml_delta.py ohne Versionsnummer
set pythonScript to scriptDirectory & "/" & "xml_delta.py"
set inputFolder to POSIX file (scriptDirectory & "/Input")

-- Benutzer auffordern, alte Datei auszuwählen
set oldXML to (choose file with prompt "Bitte wähle die ALTE XML-Datei:" default location inputFolder)
set oldXML to POSIX path of oldXML

-- Benutzer auffordern, neue Datei auszuwählen
set newXML to (choose file with prompt "Bitte wähle die NEUE XML-Datei:" default location inputFolder)
set newXML to POSIX path of newXML

-- Extrahiere Dateinamen (ohne Pfad) aus den vollständigen Pfaden
set oldFileName to do shell script "basename '" & oldXML & "'"
set newFileName to do shell script "basename '" & newXML & "'"

-- Entferne .xml Extension
set oldBaseName to do shell script "basename '" & oldFileName & "' .xml"
set newBaseName to do shell script "basename '" & newFileName & "' .xml"

-- Konstruiere neuen Deltadateinamen: alt__neu__delta.xml
set deltaFileName to oldBaseName & "__" & newBaseName & "__delta.xml"
set deltaXML to scriptDirectory & "/" & "Output" & "/" & deltaFileName

set command to "cd '" & scriptDirectory & "' && python3 '" & pythonScript & "' '" & oldXML & "' '" & newXML & "' '" & deltaXML & "'"

do shell script command

display notification "XML-Delta erfolgreich erstellt!" with title "Fertig!"
