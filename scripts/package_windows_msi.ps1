param (
    [Parameter(Mandatory=$true)]
    [string]$AppName,

    [Parameter(Mandatory=$true)]
    [string]$ExeName,

    [Parameter(Mandatory=$true)]
    [string]$SourceDir,

    [Parameter(Mandatory=$true)]
    [string]$OutputFile,

    [Parameter(Mandatory=$true)]
    [string]$UpgradeCode,

    [string]$Version = "1.0.1.0"
)

# 1. Locate WiX Toolset
$dir = Get-ChildItem "C:\Program Files (x86)\WiX Toolset*" -EA SilentlyContinue |
       Sort-Object Name -Descending | Select-Object -First 1 -ExpandProperty FullName
if (-not $dir) {
    choco install wixtoolset -y --no-progress | Out-Null
    $dir = Get-ChildItem "C:\Program Files (x86)\WiX Toolset*" |
           Sort-Object Name -Descending | Select-Object -First 1 -ExpandProperty FullName
}
if (-not $dir) {
    Write-Warning "WiX Toolset not found; skipping MSI compilation."
    exit 0
}

$wixBin = "$dir\bin"
Write-Host "WiX found at: $wixBin"

$absSource = (Resolve-Path $SourceDir).Path
Write-Host "Harvesting from: $absSource"

# 2. Harvest files
& "$wixBin\heat.exe" dir $absSource -gg -scom -sreg -srd -dr INSTALLFOLDER -cg AppComponents -var var.SourceDir -nologo -o Components.wxs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Set-Content License.rtf "{\rtf1\ansi $AppName - Internal Use Only.}" -Encoding ascii

$wxsContent = @"
<?xml version='1.0' encoding='UTF-8'?>
<Wix xmlns='http://schemas.microsoft.com/wix/2006/wi'>
  <Product Id='*' Name='$AppName' Language='1033' Version='$Version' Manufacturer='Unotusk Pvt. Ltd.' UpgradeCode='$UpgradeCode'>
    <Package InstallerVersion='500' Compressed='yes' InstallScope='perMachine' Platform='x64'/>
    <MajorUpgrade DowngradeErrorMessage='A newer version is already installed.'/>
    <MediaTemplate EmbedCab='yes'/>
    <Feature Id='ProductFeature' Title='$AppName' Level='1'>
      <ComponentGroupRef Id='AppComponents'/>
      <ComponentRef Id='DesktopShortcutComp'/>
    </Feature>
    <UIRef Id='WixUI_Minimal'/>
    <WixVariable Id='WixUILicenseRtf' Value='License.rtf'/>
  </Product>
  <Fragment>
    <Directory Id='TARGETDIR' Name='SourceDir'>
      <Directory Id='ProgramFiles64Folder'>
        <Directory Id='INSTALLFOLDER' Name='$AppName'/>
      </Directory>
      <Directory Id='DesktopFolder'/>
    </Directory>
  </Fragment>
  <Fragment>
    <DirectoryRef Id='DesktopFolder'>
      <Component Id='DesktopShortcutComp' Guid='A1B2C3D4-E5F6-7890-ABCD-111111111111' Win64='yes'>
        <Shortcut Id='DesktopShortcut' Name='$AppName' Target='[INSTALLFOLDER]$ExeName' WorkingDirectory='INSTALLFOLDER'/>
        <RegistryValue Root='HKMU' Key='Software\Unotusk\$ExeName' Name='DesktopShortcut' Type='integer' Value='1' KeyPath='yes'/>
      </Component>
    </DirectoryRef>
  </Fragment>
</Wix>
"@

[System.IO.File]::WriteAllText((Join-Path (Get-Location) 'Product.wxs'), $wxsContent)
& "$wixBin\candle.exe" -nologo -arch x64 -dSourceDir="$absSource" Product.wxs Components.wxs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& "$wixBin\light.exe" -nologo -ext WixUIExtension -sval Product.wixobj Components.wixobj -o $OutputFile
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$hash = (Get-FileHash $OutputFile -Algorithm SHA256).Hash
"$hash  $OutputFile" | Out-File "$OutputFile.sha256" -Encoding ascii
Write-Host "Successfully compiled $OutputFile (SHA256: $hash)"
