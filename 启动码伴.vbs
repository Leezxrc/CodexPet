Option Explicit
Dim shell, files, root, executable
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
root = files.GetParentFolderName(WScript.ScriptFullName)
executable = files.BuildPath(root, "app\CodexPet\CodexPet.exe")
If files.FileExists(executable) Then
  shell.Run Chr(34) & executable & Chr(34), 1, False
Else
  MsgBox "CodexPet.exe was not found. Keep the complete project folder together.", 48, "CodexPet"
End If
