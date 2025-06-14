# Test multiple Terraform environments
environments=("development" "staging" "production")

for env in "${environments[@]}"; do
    echo "🔍 Testing $env environment..."
    echo "{
        \"actions\": [\"validate\", \"plan\"],
        \"path\": \"environments/$env\",
        \"vars\": {
            \"environment\": \"$env\"
        }
    }" | docker run -i --rm \
        -v "$(pwd):/mnt/workspace" \
        terry-form-mcp python3 terry-form-mcp.py
    echo "---"
done