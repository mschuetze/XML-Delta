-- v0.3.2
#!/usr/bin/env osascript

set scriptPath to POSIX path of (path to me)
set scriptDirectory to do shell script "dirname '" & scriptPath & "'"

set pythonScript to scriptDirectory & "/xml_delta.py"
set inputFolder to POSIX file (scriptDirectory & "/Input")

set oldXML to POSIX path of (choose file with prompt "ALTE XML:" default location inputFolder)
set newXML to POSIX path of (choose file with prompt "NEUE XML:" default location inputFolder)

set oldFileName to do shell script "basename '" & oldXML & "'"
set newFileName to do shell script "basename '" & newXML & "'"
set oldBaseName to do shell script "basename '" & oldFileName & "' .xml"
set newBaseName to do shell script "basename '" & newFileName & "' .xml"
set deltaFileName to oldBaseName & "__" & newBaseName & "__delta.xml"
set deltaXML to scriptDirectory & "/Output/" & deltaFileName

-- ?? DEBUG: VollstŠndiges Terminal-Output!
set command to "cd '" & scriptDirectory & "' && python3 '" & pythonScript & "' '" & oldXML & "' '" & newXML & "' '" & deltaXML & "' 2>&1 | tee /tmp/xml_delta.log"

-- ALLES anzeigen (stdout + stderr)
set result to do shell script command

display dialog "Fertig!

Log: /tmp/xml_delta.log
" & result buttons {"Terminal šffnen", "OK"} default button "OK"

if button returned of result is "Terminal šffnen" then
	do shell script "open -a Terminal /tmp/xml_delta.log"
end if

display notification "Delta: " & deltaFileName with title "? Fertig"
