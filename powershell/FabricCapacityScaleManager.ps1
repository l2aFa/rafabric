<#
    .SYNOPSIS
        Azure Automation runbook to scale the Fabric capacity according to the specified SKU

    .NOTES
        IMPORTANT: Contributor RBAC permissions on the Fabric capacity must be assigned to the Automation account managed identity through Azure Portal
        The script performs a maximum of three retries to perform the implemented actions.
#>
[CmdletBinding()]
param
(
    [Parameter(Mandatory= $true)]
    [String]$AzureSubscriptionId = "Subscription GUID where the capacity resides",

    [Parameter(Mandatory= $true)]
    [String]$ResourceGroupName = "Resource group name where the capacity resides",

    [Parameter(Mandatory= $true)]
    [String]$CapacityName = "Fabric capacity name",

    [Parameter(Mandatory= $true)]
    [String]$ApiVersion = "Current value is 2023-11-01",

    [Parameter(Mandatory= $true)]
    [String]$SkuSize = "Specify one of the following: F2, F4, F8, F16, F32, F64, F128, F256, F512, F1024, F2048"
)

# Azure login
try {
    Write-Output("*INFO*: Logging into Azure...")
    Connect-AzAccount -Identity
}
catch {
    Write-Error -Message $_.Exception
    throw $_.Exception
}

# Initializing variables for retries and loop interruption
$StopLoop = $false
$RetryCount = 0

# Prepare request payload
$RequestPayload = @{
    sku = @{
        name = $SkuSize
        tier = 'Fabric'
        }
}
$RequestPayload = $RequestPayload | ConvertTo-Json | Out-String

# Process requested action
do {
    try {
        # Obtain capacity status and process response
        Write-Output("*INFO*: Obtaining current capacity ${CapacityName} status...")
        $CapacityResponse = Invoke-AzRestMethod -Method "GET" -Path "/subscriptions/${AzureSubscriptionId}/resourceGroups/${ResourceGroupName}/providers/Microsoft.Fabric/capacities/${CapacityName}?api-version=${ApiVersion}"
        $ResponseContent = $CapacityResponse.Content | ConvertFrom-Json
        $CapacityStatus = $ResponseContent.properties.state

        # Check status and apply appropriate action
        switch ($CapacityStatus) {
            {$_-eq "Active"} { 
                Invoke-AzRestMethod -Method "PATCH" -Path "/subscriptions/${AzureSubscriptionId}/resourceGroups/${ResourceGroupName}/providers/Microsoft.Fabric/capacities/${CapacityName}?api-version=${ApiVersion}" -Payload $RequestPayload
                Write-Output("*INFO*: Capacity ${CapacityName} has been successfully scaled to ${SkuSize} tier.")
                $StopLoop = $true 
            }
            {$_-eq "Paused"} {
                Write-Output("*WARNING*: Capacity ${CapacityName} is not running, cannot perform any action.")
                throw "Capacity ${CapacityName} is not running, please check capacity status before attempting to scale."
                $StopLoop = $true 
            }
            Default {
                Write-Output("*ERROR*: Uncontrolled case, please check the parameters provided.")
                throw "Could not retrieve capacity status, please check the parameters provided."
                $StopLoop = $true 
            }
        }
    }
    # If any error occurs, the action is reattempted up to a maximum of three times.
    catch {
        if($RetryCount -gt 3) {
            Write-Error "*ERROR*: No action could be taken on the capacity ${CapacityName} after three attempts."
            $StopLoop = $true
            throw "Unable to access the capacity after three retries. Failed to perform any action."
        }
        else {
            Write-Error -Message $_.Exception
            Write-Output "*WARNING*: No action could be taken on the capacity ${CapacityName}, retrying again in 30 seconds..."
            Start-Sleep -Seconds 30
            $RetryCount = $RetryCount + 1
        }
    }
}
While ($StopLoop -eq $false)