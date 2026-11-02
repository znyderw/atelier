# Recuperação

## Antes da migração

A integração antiga continua intacta. Feche o Atelier e use “Wallpapers e cores”.
Os dados de demonstração não são persistidos. O modo real usa sua própria pasta
`~/.local/share/atelier`, sem substituir preferências antigas durante a avaliação.

Backup funcional validado antes da implementação:
`/home/znyder/configs/backups/atelier-functional-20261030T032113Z/`.
Também permanece o backup inicial:
`/home/znyder/configs/backups/wallpaper-manager-20261029-232527/`.

Os arquivos incluem temas personalizados/default, preferências, estado por monitor,
plugin e scripts anteriores; cada archive tem manifest de hashes e VALIDATED.txt.

## Reverter uma migração instalada

O instalador imprime o caminho de um novo backup `atelier-migration-...`, contendo
`rollback.json`. Consulte primeiro o plano de reversão:

```bash
python tools/rollback.py /home/znyder/configs/backups/atelier-migration-DATA
```

Após revisão, aplique:

```bash
python tools/rollback.py /home/znyder/configs/backups/atelier-migration-DATA --apply
```

A ferramenta restaura apenas o plugin anterior e remove o launcher que criou.
Ela recusa sobrescrever arquivos modificados depois da instalação. Não apaga
os dados do Atelier, os temas ou os wallpapers, e não redefine preferências que
o usuário alterou desde a migração. O código foi testado em home temporária.

## Recuperar dados específicos

- Preferências: versões anteriores ficam em `~/.local/share/atelier/backups/`.
  Feche o app, salve a versão atual e restaure apenas o JSON necessário. O arquivo
  versionado é `~/.local/share/atelier/preferences.json`. A política consumida pela
  integração é `~/.config/omarchy/wallpaper-control.json`; após migração suas mudanças
  explícitas são espelhadas e também recebem backup antes da gravação.
- Imagens removidas: ficam em `~/.local/share/atelier/trash/`. Reimporte a imagem
  pela janela do Atelier; o conteúdo original do Workshop nunca foi removido.
- Temas removidos: a lixeira conserva o diretório com colors.toml. Salve sua versão
  atual e recupere o diretório e a entrada correspondente de preferences.json a
  partir de um backup. Os rascunhos ficam em `~/.local/share/atelier/themes/`.
- Temas `atelier-applied-*`: são transportadores gerados para preservar fundos em
  trocas de cores; não edite nem remova o tema ativo. Não houve limpeza automática.

Não extraia o arquivo compactado inteiro por cima da home. Extraia em diretório
separado, compare e recupere somente os itens necessários. Para shell.json,
restaure pontualmente; o instalador do Atelier não modifica esse arquivo.
Não use omarchy refresh para recuperar o Atelier.

A recuperação de uma paleta/default alterada por outro programa deve usar o backup
correspondente, após comparação manual. O Atelier não sobrescreve automaticamente
o default, nem durante rollback.
