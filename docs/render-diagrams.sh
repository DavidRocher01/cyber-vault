#!/usr/bin/env bash
# Régénère les diagrammes Mermaid de ARCHITECTURE.md en SVG (dossier docs/diagrams/).
# Prérequis : Node.js (npx télécharge @mermaid-js/mermaid-cli au besoin).
set -e
cd "$(dirname "$0")"
mkdir -p diagrams

# Extrait chaque bloc ```mermaid ... ``` en diagrams/NN.mmd
awk '
  /```mermaid/ { n++; f=sprintf("diagrams/%02d.mmd", n); inb=1; next }
  /```/        { inb=0 }
  inb          { print > f }
' ARCHITECTURE.md

# Rend chaque .mmd en SVG (fond blanc pour lisibilité sur toute page)
for m in diagrams/*.mmd; do
  echo "→ ${m%.mmd}.svg"
  npx -y @mermaid-js/mermaid-cli -i "$m" -o "${m%.mmd}.svg" -b white -t default
done
echo "OK — $(ls diagrams/*.svg | wc -l) diagrammes SVG générés."
