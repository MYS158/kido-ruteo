#!/bin/bash
# Script para limpiar ramas de Git locales y remotas.
# Uso: bash scripts/clean_branches.sh

echo "=== Limpieza de Ramas Git ==="
echo ""

# Actualizar referencias remotas
echo "Actualizando referencias remotas..."
git fetch --prune

# Mostrar ramas locales
echo ""
echo "Ramas locales:"
git branch

# Mostrar ramas remotas
echo ""
echo "Ramas remotas:"
git branch -r

echo ""
echo "Para eliminar una rama local:"
echo "  git branch -d <nombre-rama>"
echo ""
echo "Para eliminar una rama remota:"
echo "  git push origin --delete <nombre-rama>"
