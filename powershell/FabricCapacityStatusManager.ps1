<#
    .SYNOPSIS
        Azure Automation runbook to start and stop Fabric capacity according to the specified action

    .NOTES
        IMPORTANT: Contributor RBAC permissions on the Fabric capacity must be assigned to the Automation account managed identity through Azure Portal
        The script performs a maximum of three retries to perform the implemented actions.
#>
[CmdletBinding()]
param (
    [Parameter(Mandatory= $true)]
    [String]$AzureSubscriptionId = "Subscription GUID where the capacity resides",

    [Parameter(Mandatory= $true)]
    [String]$ResourceGroupName = "Resource group name where the capacity resides",

    [Parameter(Mandatory= $true)]
    [String]$Action = "Use resume to start and suspend to stop",

    [Parameter(Mandatory= $true)]
    [String]$CapacityName = "Fabric capacity name",

    [Parameter(Mandatory= $true)]
    [String]$ApiVersion = "Current value is 2023-11-01"
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

# Process requested action
do {
    try {
        # Obtain capacity status and process response
        Write-Output("*INFO*: Obtaining current capacity ${CapacityName} status...")
        $CapacityResponse = Invoke-AzRestMethod -Method "GET" -Path "/subscriptions/${AzureSubscriptionId}/resourceGroups/${ResourceGroupName}/providers/Microsoft.Fabric/capacities/${CapacityName}?api-version=${ApiVersion}"
        $ResponseContent = $CapacityResponse.Content | ConvertFrom-Json
        $CapacityStatus = $ResponseContent.properties.state
        
        # Check status and apply appropriate action
        Write-Output("*INFO*: The current state of capacity ${CapacityName} is ${CapacityStatus}. Applying requested action ${Action}...")
        switch ($CapacityStatus) {
            {$_-eq "Active" -And $Action -eq "resume"} { 
                Write-Output("*INFO*: Capacity ${CapacityName} is already running.") 
                $StopLoop = $true 
            }
            {$_-eq "Paused" -And $Action -eq "resume"} {
                $ActionResponse = Invoke-AzRestMethod -Method "POST" -Path "/subscriptions/${AzureSubscriptionId}/resourceGroups/${ResourceGroupName}/providers/Microsoft.Fabric/capacities/${CapacityName}/${Action}?api-version=${ApiVersion}"
                if($ActionResponse.StatusCode -eq 202) {
                    Write-Output("*INFO*: Capacity ${CapacityName} has been successfully started.")
                }
                $StopLoop = $true
            }
            {$_-eq "Paused" -And $Action -eq "suspend"} {
                Write-Output("*INFO*: Capacity ${CapacityName} is already stopped.")
                $StopLoop = $true
            }
            {$_-eq "Active" -And $Action -eq "suspend"} {
                $ActionResponse = Invoke-AzRestMethod -Method "POST" -Path "/subscriptions/${AzureSubscriptionId}/resourceGroups/${ResourceGroupName}/providers/Microsoft.Fabric/capacities/${CapacityName}/${Action}?api-version=${ApiVersion}"
                if($ActionResponse.StatusCode -eq 202) {
                    Write-Output("*INFO*: Capacity ${CapacityName} has been successfully stopped.")
                }
                $StopLoop = $true
            }
            Default {
                Write-Output("*ERROR*: Uncontrolled case, please check the parameters provided.")
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