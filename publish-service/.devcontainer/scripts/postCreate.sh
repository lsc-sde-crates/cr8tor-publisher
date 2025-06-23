git config --global --add safe.directory /workspaces/cr8tor-publisher

# Process TARGET_STORAGE_ACCOUNT environment variables
echo "Setting up storage account directories..."
for var in $(env | grep '^TARGET_STORAGE_ACCOUNT_.*_SDE_MNT_PATH=' | cut -d'=' -f1); do
    path=$(eval echo \$$var)
    if [ ! -z "$path" ]; then
        echo "Creating directories for $var: $path"
        mkdir -p "$path/staging" "$path/production"
        # Ensure proper permissions
        chown -R vscode:vscode "$path"
    fi
done