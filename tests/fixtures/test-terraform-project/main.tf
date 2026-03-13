# Test Terraform configuration for LSP integration demo
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Resource Group with some intentional issues for LSP testing
resource "azurerm_resource_group" "example" {
  name     = "rg-example"
  location = "East US"
  
  tags = {
    Environment = "test"
    Project     = "lsp-demo"
  }
}

# Storage Account - will test LSP completion and validation
resource "azurerm_storage_account" "example" {
  name                = "stexample"
  resource_group_name = azurerm_resource_group.example.name
  location            = azurerm_resource_group.example.location
  account_tier        = "Standard"
  account_replication_type = "LRS"
  
  # This line will have validation issues for testing
  allow_blob_public_access = true
}

# Virtual Network for testing hover documentation
resource "azurerm_virtual_network" "example" {
  name                = "vnet-example"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.example.location
  resource_group_name = azurerm_resource_group.example.name
}

# Intentional syntax error for validation testing
resource "azurerm_subnet" "example" {
  name                 = "subnet-internal"
  resource_group_name  = azurerm_resource_group.example.name
  virtual_network_name = azurerm_virtual_network.example.name
  address_prefixes     = ["10.0.2.0/24"]
  # Missing required argument 'address_prefix' or incorrect syntax
}
