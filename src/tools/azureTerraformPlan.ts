import { execSync } from 'child_process';
import path from 'path';

export async function azureTerraformPlan(directory: string): Promise<string> {
  const fullPath = path.resolve(directory);
  console.log(`Executing Azure Terraform plan in ${fullPath}`);

  try {
    // Validate Azure CLI authentication
    const azAccount = execSync('az account show', { encoding: 'utf-8' });
    console.log('Azure CLI authenticated:', azAccount);
  } catch (err) {
    throw new Error('Azure CLI not authenticated. Please run `az login` first.');
  }

  try {
    execSync(`terraform init`, { cwd: fullPath, stdio: 'inherit' });
    const planOutput = execSync(`terraform plan`, { cwd: fullPath, encoding: 'utf-8' });
    console.log('Terraform plan executed successfully.');
    return planOutput;
  } catch (err) {
    throw new Error(`Terraform execution failed: ${err}`);
  }
}
