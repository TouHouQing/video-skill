param([Parameter(Mandatory=$true)][string]$TextFile,
      [Parameter(Mandatory=$true)][string]$OutputFile)
$ErrorActionPreference = 'Stop'
$taskSpeech = New-Object -ComObject SAPI.SpVoice
$taskChinese = @($taskSpeech.GetVoices() | Where-Object { $_.GetAttribute('Language') -match '(^|;)804(;|$)' })
if ($taskChinese.Count -eq 0) { throw 'No installed Simplified Chinese SAPI voice. Install a Chinese speech voice in Windows language settings.' }
$taskSpeech.Voice = $taskChinese[0]
$taskSpeech.Rate = 1
$taskSpeech.Volume = 100
$taskStream = New-Object -ComObject SAPI.SpFileStream
$taskStream.Format.Type = 22
try {
    $taskStream.Open($OutputFile, 3, $false)
    $taskSpeech.AudioOutputStream = $taskStream
    $taskText = [System.IO.File]::ReadAllText($TextFile, [System.Text.Encoding]::UTF8)
    $null = $taskSpeech.Speak($taskText, 0)
} finally {
    $taskStream.Close()
}
Write-Output $taskSpeech.Voice.GetDescription()
