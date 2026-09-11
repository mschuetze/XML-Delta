#!/usr/bin/env osascript
-- v0.3.5

set scriptPath to POSIX path of (path to me)
set scriptDirectory to do shell script "dirname '" & scriptPath & "'"

set pythonScript to scriptDirectory & "/xml_delta.py"
set logPath to scriptDirectory & "/Output/xml_delta.txt"

set command to "cd '" & scriptDirectory & "' && python3 '" & pythonScript & "' >/dev/null 2>&1"

try
	do shell script command
	display dialog "XML-Delta erfolgreich! Eine Log-Datei wurde erzeugt." buttons {"OK"} default button "OK"
	do shell script "open " & quoted form of logPath
	display notification "XML-Delta abgeschlossen" with title "Fertig"
on error errorMessage
	try
		set logContent to do shell script "cat " & quoted form of logPath
	on error
		set logContent to errorMessage
	end try
	display dialog "XML-Delta fehlgeschlagen:" & return & logContent buttons {"OK"} default button "OK" with icon stop
end try
