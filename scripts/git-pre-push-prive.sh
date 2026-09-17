#!/usr/bin/env bash
# git-pre-push-prive.sh — LE VERROU « privé = local uniquement » (metrox 04/09/2026 13h28 :
# « il faut blinder ça pour que ça n'arrive plus, les trucs privés ça devrait être en local uniquement »).
# Installé comme .git/hooks/pre-push dans les dépôts qui portent du privé. Il refuse TOUT push, sauf
# ALLOW_PUSH=1 explicite ET aucun fichier de la liste privée dans la plage poussée.
# Né du palais poussé sur GitHub par la boucle RSI (20-27/05/2026, découvert le 02/09).
set -u
REPO="$(git rev-parse --show-toplevel)"
case "$REPO" in
  */memory) echo "✗ pre-push : le PALAIS ne se pousse JAMAIS, nulle part (règle absolue)." >&2; exit 1;;
esac
PRIVE_RE='^(CURRENT\.md|TODO\.md|PRIVE.*|prive/|_perime/CURRENT_|_perime/ORDRES_|docs/charte_magicien|docs/love_first|docs/dossier_showrobotics|docs/astra_|docs/vita_camping|docs/discord_recon|docs/dossier_pitch|docs/journal|docs/reves|docs/reveils|docs/.*prive|.*secrets\.env|.*\.env$|infra/wg0)'
if [ "${ALLOW_PUSH:-0}" != "1" ]; then
  echo "✗ pre-push refusé : ce dépôt porte du privé (CURRENT, TODO, journaux, recon). Un push demande" >&2
  echo "  ALLOW_PUSH=1 explicite ET une plage sans fichier privé. Le hors-site du privé = backup chiffré, pas GitHub." >&2
  exit 1
fi
# plage poussée : lit stdin (local_ref local_sha remote_ref remote_sha)
Z=0000000000000000000000000000000000000000
while read -r lref lsha rref rsha; do
  [ "$lsha" = "$Z" ] && continue
  if [ "$rsha" = "$Z" ]; then
    # branche neuve chez le distant : TOUT l'arbre part -> on regarde tout l'arbre
    hits=$(git ls-tree -r --name-only "$lsha" 2>/dev/null | grep -E "$PRIVE_RE" | head -5)
  else
    hits=$(git diff --name-only "$rsha..$lsha" 2>/dev/null | grep -E "$PRIVE_RE" | head -5)
  fi
  if [ -n "$hits" ]; then
    echo "✗ pre-push refusé : la plage $rref contient du privé :" >&2; echo "$hits" | sed 's/^/    /' >&2; exit 1
  fi
done
echo "pre-push : ALLOW_PUSH=1, aucun fichier privé dans la plage - push autorisé" >&2
exit 0
