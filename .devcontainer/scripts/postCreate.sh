git config --global --add safe.directory /workspaces/cr8tor-publisher
git config --global init.defaultBranch main
cd /workspaces/stroma

cat >> ~/.inputrc <<'EOF'
"\e[A": history-search-backward
"\e[B": history-search-forward
EOF

uv sync
