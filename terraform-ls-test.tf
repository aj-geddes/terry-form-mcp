terraform {
  required_version = ">= 1.0"
}

# Test terraform-ls binary availability
data "external" "terraform_ls_check" {
  program = ["sh", "-c", "echo '{\"terraform_ls_available\": \"'$(which terraform-ls > /dev/null 2>&1 && echo true || echo false)'\", \"terraform_ls_version\": \"'$(terraform-ls version 2>/dev/null || echo 'not available')'\", \"current_path\": \"'$PATH'\"}'"]
}

output "terraform_ls_check" {
  value = data.external.terraform_ls_check.result
}
