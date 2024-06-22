# **▶️ PowerShell ▶️**
Scripts to automate actions over a Fabric capacity through an Azure Automation account.

---

## 1️⃣ Prerequisites:
-	A Microsoft Fabric Capacity in the Azure portal.
-   An Azure Automation account in the Azure portal.
    - In the **Access Control(IAM)** menu for the Fabric Capacity, add the Azure Automation managed identity as Contributor, allowing Automation to modify the capacity.
-	Add the desired scripts as PowerShell 7.2 runbooks inside Azure Automation.
    - Fill out the default parameters for each runbook with your Fabric capacity information. You will find the values on the **Overview** page of the capacity in the Azure portal. 
    - Schedule the runbooks as desired or add a webhook to call them from a Fabric Data Factory pipeline. You would not be able to start a capacity from within a Fabric pipeline if is not running.

## 2️⃣ Contents:
-   [FabricCapacityScaleManager](https://github.com/l2aFa/rafabric/blob/main/powershell/FabricCapacityScaleManager.ps1): Script to automate the scaling of a Fabric capacity through an Azure Automation account.
-   [FabricCapacityStatusmanager](https://github.com/l2aFa/rafabric/blob/main/powershell/FabricCapacityStatusManager.ps1): Script to automate the start and/or stop of a Fabric capacity through an Azure Automation account.