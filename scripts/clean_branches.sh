#!/bin/bash
# Script para limpiar ramas Git obsoletas
# Preserva el historial del repositorio

echo "========================================="
echo "KIDO-Ruteo - Limpieza de Ramas Git"
echo "========================================="

# Mostrar rama actual
echo ""
echo "📍 Rama actual:"
git branch --show-current

# Listar todas las ramas locales
echo ""
echo "📋 Ramas locales existentes:"
git branch

# Confirmar antes de proceder
echo ""
read -p "¿Deseas eliminar las ramas locales excepto 'main' y la rama actual? (y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo ""
    echo "🗑️  Eliminando ramas locales (excepto main y rama actual)..."
    
    # Obtener rama actual
    current_branch=$(git branch --show-current)
    
    # Eliminar todas las ramas excepto main y la actual
    git branch | grep -v "main" | grep -v "$current_branch" | grep -v "\*" | xargs -r git branch -D
    
    echo "✅ Ramas locales limpiadas"
fi

# Limpiar referencias remotas obsoletas
echo ""
echo "🔄 Limpiando referencias remotas obsoletas..."
git fetch --all --prune

echo ""
echo "✅ Limpieza completada"
echo ""
echo "📋 Ramas locales restantes:"
git branch

echo ""
echo "📋 Ramas remotas:"
git branch -r

echo ""
echo "========================================="
echo "✅ Proceso de limpieza finalizado"
echo "========================================="
