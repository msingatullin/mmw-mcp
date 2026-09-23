param(
  [ValidateSet('claude','cursor','gemini','codex','generic')][string]$Client='generic',
  [string]$Workspace='default',
  [switch]$Verify,
  [switch]$Uninstall,
  [switch]$Help
)
$ErrorActionPreference='Stop'
$endpoint=if($env:MMW_ENDPOINT){$env:MMW_ENDPOINT}else{'https://mcp.mmwhub.tech/mcp'}
$dir=Join-Path $env:APPDATA 'MMW'
$secret=Join-Path $dir 'credential'

if($Help){
  Write-Output 'Usage: ./connect.ps1 -Client claude|cursor|gemini|codex|generic [-Verify] [-Uninstall]'
  exit 0
}

if($Client -eq 'claude'){$path=Join-Path $env:APPDATA 'Claude\claude_desktop_config.json'}
elseif($Client -eq 'cursor'){$path=Join-Path $env:USERPROFILE '.cursor\mcp.json'}
elseif($Client -eq 'gemini'){$path=Join-Path $env:USERPROFILE '.gemini\mmw-mcp.json'}
else{$path=$null}

if($Uninstall){
  Remove-Item $secret -Force -ErrorAction SilentlyContinue
  if($path){Remove-Item $path -Force -ErrorAction SilentlyContinue}
  Write-Output 'MMW local credential and generated client config removed'
  exit 0
}

New-Item $dir -ItemType Directory -Force | Out-Null
if(-not $env:MMW_CREDENTIAL -and (Test-Path $secret)){$env:MMW_CREDENTIAL=[IO.File]::ReadAllText($secret)}
if(-not $env:MMW_CREDENTIAL){
  $secure=Read-Host 'MMW credential' -AsSecureString
  $ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try{$env:MMW_CREDENTIAL=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)}
  finally{[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)}
}
if(-not $env:MMW_CREDENTIAL){throw 'MMW credential is required'}
[IO.File]::WriteAllText($secret,$env:MMW_CREDENTIAL)

$server=[ordered]@{
  url=$endpoint
  headers=@{Authorization="Bearer $env:MMW_CREDENTIAL"}
  workspace=$Workspace
}
if($path){
  New-Item (Split-Path $path) -ItemType Directory -Force | Out-Null
  [IO.File]::WriteAllText($path,(@{mcpServers=@{mmw=$server}} | ConvertTo-Json -Depth 6))
  Write-Output "MMW client config written: $path"
}elseif($Client -eq 'codex'){
  Write-Output "[mcp_servers.mmw]`nurl = `"$endpoint`"`nbearer_token_env_var = `"MMW_CREDENTIAL`""
}else{$server | ConvertTo-Json -Depth 4}

if($Verify){
  $body='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"mmw-connect-kit","version":"1.0"}}}'
  Invoke-WebRequest $endpoint -Method Post -Headers @{Authorization="Bearer $env:MMW_CREDENTIAL";Accept='application/json, text/event-stream'} -ContentType 'application/json' -Body $body | Out-Null
  Write-Output 'MMW MCP connection verified'
}
