#!/usr/bin/env pwsh

$ErrorActionPreference = "Stop"

Write-Host "Stopping MarketMonitor services..."

Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like "*stream_service*"} | Stop-Process -Force
Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like "*ui.backend*"} | Stop-Process -Force
Get-Process streamlit -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like "*streamlit run*"} | Stop-Process -Force

Write-Host "Services stopped."
