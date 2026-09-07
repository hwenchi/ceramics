#!/bin/bash
# Idempotent: fetches any book not already present, then (re)builds the index.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="/var/lib/recipes/gutenberg-search"
CORPUS_DIR="$DATA_DIR/corpus"
mkdir -p "$CORPUS_DIR"

declare -A books=(
  [1342]="Pride_and_Prejudice"
  [2701]="Moby_Dick"
  [84]="Frankenstein"
  [11]="Alices_Adventures_in_Wonderland"
  [98]="A_Tale_of_Two_Cities"
  [1661]="Adventures_of_Sherlock_Holmes"
  [345]="Dracula"
  [2600]="War_and_Peace"
  [2554]="Crime_and_Punishment"
  [174]="The_Picture_of_Dorian_Gray"
  [1260]="Jane_Eyre"
  [768]="Wuthering_Heights"
  [76]="Adventures_of_Huckleberry_Finn"
  [74]="The_Adventures_of_Tom_Sawyer"
  [120]="Treasure_Island"
  [1400]="Great_Expectations"
  [514]="Little_Women"
  [33]="The_Scarlet_Letter"
  [1399]="Anna_Karenina"
  [4300]="Ulysses"
  [5200]="Metamorphosis"
  [35]="The_Time_Machine"
  [219]="Heart_of_Darkness"
  [2591]="Grimms_Fairy_Tales"
  [1184]="The_Count_of_Monte_Cristo"
)

for id in "${!books[@]}"; do
  name="${books[$id]}"
  dest="$CORPUS_DIR/$name.txt"
  if [[ ! -s "$dest" ]]; then
    echo "fetching $name..."
    curl -sS -L -o "$dest" "https://www.gutenberg.org/cache/epub/${id}/pg${id}.txt" || rm -f "$dest"
  fi
done

python3 "$SCRIPT_DIR/index.py"
