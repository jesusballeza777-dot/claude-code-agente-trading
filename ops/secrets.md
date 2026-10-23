# Secretos con SOPS + age

**Estado:** preparado; falta la clave pública del propietario · **Fuentes:** CLAUDE.md regla 1; ADR-005 (criterio de salida de la F2)

Los secretos (claves de exchange, token de Telegram, clave de la API de Anthropic) se guardan **cifrados** en el repositorio
y solo se descifran en tiempo de ejecución en la máquina que opera. Nunca se escriben en claro en código, logs, tests, prompts ni commits.

## Puesta en marcha (la hace el propietario, en su ordenador)

1. Instalar `age` y `sops` (Homebrew: `brew install age sops`; Linux: paquetes de la distribución o binarios oficiales).
2. Generar la clave **en tu ordenador**, nunca en una sesión remota:
   ```bash
   mkdir -p ~/.config/sops/age
   age-keygen -o ~/.config/sops/age/keys.txt
   ```
   El fichero `keys.txt` contiene la **clave privada**: no sale de tu ordenador (haz una copia de seguridad offline).
3. El comando muestra una línea `Public key: age1...`. Esa clave **pública** no es secreta: pásala para crear `.sops.yaml`.
4. Con la clave pública, `.sops.yaml` en la raíz queda así:
   ```yaml
   creation_rules:
     - path_regex: secrets/.*\.sops\.ya?ml$
       age: age1...   # clave pública del propietario (y la del VPS cuando exista)
   ```
5. Crear y editar secretos siempre a través de sops: `sops secrets/exchange.sops.yaml`. El fichero queda cifrado y se puede versionar.

## Reglas

- `.gitignore` bloquea todo lo que hay en `secrets/` salvo los ficheros cifrados `*.sops.yaml`, además de `.env`, `*.key`, `keys.txt` y similares; gitleaks corre en pre-commit y en CI.
- El VPS tendrá su propia clave age; se añade como segundo destinatario en `.sops.yaml` y se rota si el VPS se reemplaza.
- Si una clave de exchange se expone: revocarla en el exchange al momento, crear otra y registrar el incidente en `ops/incidents/`.
