#!/bin/bash
# Arreglar cd-secure.yml
cat > cd-secure.yml.tmp << 'YAML'
# ⚠️ WORKFLOW DESHABILITADO - Ver ci.yml para tests básicos
name: CD - Secure OIDC Deployment (Disabled)

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy'
        required: true
        type: choice
        options:
          - dev
          - staging
          - production
  # Deshabilitado: se ejecuta solo manualmente
  # push:
  #   branches: [main, staging]
YAML
head -1 cd-secure.yml.tmp > temp && tail -n +8 cd-secure.yml >> temp && mv temp cd-secure.yml
rm cd-secure.yml.tmp
