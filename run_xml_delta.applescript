#!/usr/bin/env osascript

set scriptPath to POSIX path of (path to me)
set scriptDirectory to do shell script "dirname '" & scriptPath & "'"

set pythonScript to scriptDirectory & "/" & "xml_delta_v0.1.0.py"
set deltaXML to scriptDirectory & "/" & "Output" & "/" & "delta.xml"
set inputFolder to POSIX file (scriptDirectory & "/Input")

-- Benutzer auffordern, alte Datei auszuwählen
set oldXML to (choose file with prompt "Bitte wähle die ALTE XML-Datei:" default location inputFolder)
set oldXML to POSIX path of oldXML

-- Benutzer auffordern, neue Datei auszuwählen
set newXML to (choose file with prompt "Bitte wähle die NEUE XML-Datei:" default location inputFolder)
set newXML to POSIX path of newXML

set command to "cd '" & scriptDirectory & "' && python3 '" & pythonScript & "' '" & oldXML & "' '" & newXML & "' '" & deltaXML & "'"

do shell script command

display notification "XML-Delta erfolgreich erstellt!" with title "Fertig!"
